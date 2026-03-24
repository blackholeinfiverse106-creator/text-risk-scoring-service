"""
Bucket Ledger
==============
Persistent, append-only enforcement decision ledger backed by JSONL file storage.

Each enforcement evaluation produces a BucketEntry containing:
  - action_id and bucket_id
  - input_snapshot_hash (SHA-256 of all inputs)
  - decision output and risk metrics
  - trace_hash (deterministic replay key)
  - trace_lineage (previous bucket → current, forming a chain)
  - replay_proof (SHA-256 of the full entry for tamper detection)

Storage format: one JSON object per line in data/enforcement_bucket.jsonl
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# ============================================================
# Constants
# ============================================================

BUCKET_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "enforcement_bucket.jsonl",
)


# ============================================================
# Input Snapshot Hash
# ============================================================

def compute_input_snapshot_hash(
    request_payload: Dict[str, Any],
    dgic_snapshot: Dict[str, Any],
) -> str:
    """
    Compute a deterministic SHA-256 hash of ALL enforcement inputs.
    This proves exactly what data was evaluated.
    """
    canonical = {
        "request": request_payload,
        "dgic_snapshot": dgic_snapshot,
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ============================================================
# Replay Proof
# ============================================================

def compute_replay_proof(entry_dict: Dict[str, Any]) -> str:
    """
    Compute a SHA-256 hash of the full bucket entry (excluding replay_proof itself).
    Used for tamper detection on stored entries.
    """
    # Create a copy without replay_proof to avoid circular hashing
    proof_input = {k: v for k, v in entry_dict.items() if k != "replay_proof"}
    raw = json.dumps(proof_input, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ============================================================
# Bucket Entry
# ============================================================

@dataclass(frozen=True)
class BucketEntry:
    """
    A single, immutable bucket ledger entry.
    Contains all information needed for deterministic replay verification.
    """
    bucket_id: str
    action_id: str
    timestamp_utc: str

    # Input proof
    input_snapshot_hash: str  # SHA-256 of request + DGIC snapshot
    request_payload: Dict[str, Any]
    dgic_snapshot: Dict[str, Any]

    # Decision output
    decision: str
    risk_score: float
    confidence: float
    failure_reason: Optional[str]

    # Replay infrastructure
    trace_hash: str          # Deterministic replay key
    trace_lineage: str       # "GENESIS" or previous bucket_id
    replay_proof: str        # SHA-256 of this entry for tamper detection


# ============================================================
# Bucket Ledger (File-Persistent, Thread-Safe)
# ============================================================

class BucketLedger:
    """
    Persistent, append-only bucket ledger backed by JSONL file.
    Thread-safe for concurrent writes.
    """

    def __init__(self, file_path: str = BUCKET_FILE):
        self._file_path = file_path
        self._lock = threading.RLock()
        self._last_bucket_id: Optional[str] = None

        # Load last bucket_id for trace lineage
        self._initialize_lineage()

    def _initialize_lineage(self) -> None:
        """Load the last bucket_id from existing entries for chain continuity."""
        if os.path.exists(self._file_path):
            try:
                entries = self._read_all_raw()
                if entries:
                    self._last_bucket_id = entries[-1].get("bucket_id")
            except Exception:
                self._last_bucket_id = None

    def write(
        self,
        action_id: str,
        request_payload: Dict[str, Any],
        dgic_snapshot: Dict[str, Any],
        decision: str,
        risk_score: float,
        confidence: float,
        failure_reason: Optional[str],
        trace_hash: str,
    ) -> BucketEntry:
        """
        Write a new bucket entry to the persistent ledger.
        Automatically computes bucket_id, input_snapshot_hash, trace_lineage, and replay_proof.
        """
        bucket_id = str(uuid.uuid4())
        timestamp_utc = datetime.now(timezone.utc).isoformat()

        # Compute input snapshot hash
        input_snapshot_hash = compute_input_snapshot_hash(request_payload, dgic_snapshot)

        # Determine trace lineage
        with self._lock:
            trace_lineage = self._last_bucket_id or "GENESIS"

        # Build entry dict for replay proof computation (without replay_proof)
        entry_dict = {
            "bucket_id": bucket_id,
            "action_id": action_id,
            "timestamp_utc": timestamp_utc,
            "input_snapshot_hash": input_snapshot_hash,
            "request_payload": request_payload,
            "dgic_snapshot": dgic_snapshot,
            "decision": decision,
            "risk_score": risk_score,
            "confidence": confidence,
            "failure_reason": failure_reason,
            "trace_hash": trace_hash,
            "trace_lineage": trace_lineage,
        }

        # Compute replay proof
        replay_proof = compute_replay_proof(entry_dict)

        # Build frozen entry
        entry = BucketEntry(
            bucket_id=bucket_id,
            action_id=action_id,
            timestamp_utc=timestamp_utc,
            input_snapshot_hash=input_snapshot_hash,
            request_payload=request_payload,
            dgic_snapshot=dgic_snapshot,
            decision=decision,
            risk_score=risk_score,
            confidence=confidence,
            failure_reason=failure_reason,
            trace_hash=trace_hash,
            trace_lineage=trace_lineage,
            replay_proof=replay_proof,
        )

        # Append to file
        with self._lock:
            os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
            with open(self._file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(entry), sort_keys=True, separators=(",", ":")) + "\n")
            self._last_bucket_id = bucket_id

        logger.info(
            f"Bucket entry written | bucket_id={bucket_id[:8]}...",
            extra={
                "event_type": "bucket_write",
                "bucket_id": bucket_id,
                "action_id": action_id,
                "decision": decision,
                "trace_lineage": trace_lineage[:8] + "..." if trace_lineage != "GENESIS" else "GENESIS",
            },
        )

        return entry

    def _read_all_raw(self) -> List[Dict[str, Any]]:
        """Read all raw JSON entries from the JSONL file."""
        if not os.path.exists(self._file_path):
            return []
        entries = []
        with open(self._file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def read_all(self) -> List[BucketEntry]:
        """Read all bucket entries from the persistent store."""
        with self._lock:
            raw_entries = self._read_all_raw()
        return [BucketEntry(**e) for e in raw_entries]

    def get_by_trace_hash(self, trace_hash: str) -> Optional[BucketEntry]:
        """Lookup a bucket entry by its deterministic trace hash."""
        entries = self.read_all()
        for entry in entries:
            if entry.trace_hash == trace_hash:
                return entry
        return None

    def get_chain(self) -> List[BucketEntry]:
        """Return all entries ordered by insertion (trace lineage chain)."""
        return self.read_all()

    def clear(self) -> None:
        """Clear the bucket file (for testing only)."""
        with self._lock:
            if os.path.exists(self._file_path):
                os.remove(self._file_path)
            self._last_bucket_id = None


# ============================================================
# Global Singleton
# ============================================================

bucket_ledger = BucketLedger()


# ============================================================
# Public API
# ============================================================

def write_bucket_entry(
    action_id: str,
    request_payload: Dict[str, Any],
    dgic_snapshot: Dict[str, Any],
    decision: str,
    risk_score: float,
    confidence: float,
    failure_reason: Optional[str],
    trace_hash: str,
) -> BucketEntry:
    return bucket_ledger.write(
        action_id=action_id,
        request_payload=request_payload,
        dgic_snapshot=dgic_snapshot,
        decision=decision,
        risk_score=risk_score,
        confidence=confidence,
        failure_reason=failure_reason,
        trace_hash=trace_hash,
    )


def get_bucket_entries() -> List[BucketEntry]:
    return bucket_ledger.read_all()


def get_bucket_entry(trace_hash: str) -> Optional[BucketEntry]:
    return bucket_ledger.get_by_trace_hash(trace_hash)


def get_bucket_chain() -> List[BucketEntry]:
    return bucket_ledger.get_chain()


def clear_bucket() -> None:
    bucket_ledger.clear()
