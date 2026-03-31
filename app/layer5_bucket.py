from __future__ import annotations
"""
Sovereign Layer File: app/layer5_bucket.py

Bucket Ledger — External API adapter for Primary_Bucket_Owner service.

ALL persistence is external. This module contains:
  1. write_execution_record(payload) — submit execution record to Bucket
  2. verify_execution(trace_hash) — replay-verify a past execution
  3. Helper read methods for bucket entries

Authority Boundary:
  - This module ONLY adapts formatting and handles the network border.
  - Failures fail-open (log error, allow execution) as per architecture policy.
  - NO local storage. All data lives in the external Bucket service.
"""


import hashlib
import json
import logging
import os
import requests
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# External service configuration
BUCKET_SERVICE_URL = os.environ.get("BUCKET_SERVICE_URL", "http://localhost:8000")


# ============================================================
# Hash Computation
# ============================================================

def compute_artifact_hash(artifact_dict: Dict[str, Any]) -> str:
    """
    Compute deterministic SHA-256 hash required by the external
    Bucket service envelope specification.
    """
    # Create copy without artifact_hash to avoid circular hashing
    proof_input = {k: v for k, v in artifact_dict.items() if k != "artifact_hash"}
    raw = json.dumps(proof_input, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ============================================================
# write_execution_record — Canonical Write API (Phase 4)
# ============================================================

def write_execution_record(
    execution_id: str,
    decision: str,
    risk_score: float,
    confidence: float,
    trace_hash: str,
    request_payload: Optional[Dict[str, Any]] = None,
    dgic_snapshot: Optional[Dict[str, Any]] = None,
    failure_reason: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Submit an execution record to the external Bucket service.

    This is the ONLY write path. No local storage.
    Fails open: catches all exceptions, logs them, returns None.

    Returns the artifact dict on success, None on failure.
    """
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    execution_payload = {
        "request_payload": request_payload or {},
        "dgic_snapshot": dgic_snapshot or {},
        "decision": decision,
        "risk_score": risk_score,
        "confidence": confidence,
        "failure_reason": failure_reason,
        "trace_hash": trace_hash,
    }

    artifact = {
        "artifact_id": execution_id,
        "source_module_id": "bhiv_enforcement_gate",
        "schema_version": "1.0.0",
        "timestamp_utc": timestamp_utc,
        "artifact_type": "truth_event",
        "payload": execution_payload,
    }

    artifact["artifact_hash"] = compute_artifact_hash(artifact)

    target_url = f"{BUCKET_SERVICE_URL.rstrip('/')}/bucket/artifact"

    try:
        logger.info(
            f"Dispatching artifact to external bucket | execution_id={execution_id}",
            extra={
                "event_type": "bucket_dispatch_start",
                "execution_id": execution_id,
                "target_url": target_url,
            },
        )
        response = requests.post(
            target_url,
            json=artifact,
            headers={"Content-Type": "application/json"},
            timeout=3.0,
        )
        response.raise_for_status()

        logger.info(
            f"Artifact successfully stored in external bucket | execution_id={execution_id}",
            extra={
                "event_type": "bucket_dispatch_success",
                "execution_id": execution_id,
            },
        )
        return artifact

    except requests.exceptions.RequestException as e:
        # FAIL OPEN POLICY
        logger.error(
            f"External bucket recording failed | execution_id={execution_id} | error={str(e)}",
            exc_info=True,
            extra={
                "event_type": "bucket_dispatch_failed",
                "execution_id": execution_id,
                "target_url": target_url,
                "error": str(e),
            },
        )
        return None


# ============================================================
# Backward-compatible alias: write_bucket_entry
# ============================================================

def write_bucket_entry(
    execution_id: str,
    request_payload: Dict[str, Any],
    dgic_snapshot: Dict[str, Any],
    decision: str,
    risk_score: float,
    confidence: float,
    failure_reason: Optional[str],
    trace_hash: str,
) -> Optional[Dict[str, Any]]:
    """
    Legacy adapter — calls write_execution_record with the old signature.
    """
    return write_execution_record(
        execution_id=execution_id,
        decision=decision,
        risk_score=risk_score,
        confidence=confidence,
        trace_hash=trace_hash,
        request_payload=request_payload,
        dgic_snapshot=dgic_snapshot,
        failure_reason=failure_reason,
    )


# ============================================================
# API Read Methods
# ============================================================

def get_bucket_entries(limit: int = 100, offset: int = 0) -> list[Dict[str, Any]]:
    """Fetch raw artifacts from the external Bucket service."""
    target_url = f"{BUCKET_SERVICE_URL.rstrip('/')}/bucket/artifacts"
    try:
        response = requests.get(target_url, params={"limit": limit, "offset": offset}, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch bucket entries from {target_url}: {e}")
        return []


def get_bucket_entry(artifact_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a specific artifact from the external Bucket service by its ID."""
    target_url = f"{BUCKET_SERVICE_URL.rstrip('/')}/bucket/artifact/{artifact_id}"
    try:
        response = requests.get(target_url, timeout=3.0)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch bucket entry {artifact_id} from {target_url}: {e}")
        return None


# ============================================================
# verify_execution — Canonical Verify API (Phase 4)
# ============================================================

from app.enforcement_schemas import EvaluateActionRequest
from app.layer1_sarathi import evaluate_action


@dataclass(frozen=True)
class ReplayResult:
    """Result of replaying a single bucket entry (artifact)."""
    bucket_id: str
    trace_hash: str
    original_decision: str
    replayed_decision: str
    original_risk_score: float
    replayed_risk_score: float
    match: bool
    replay_proof_valid: bool
    error: Optional[str]


def verify_execution(trace_hash: str) -> Optional[ReplayResult]:
    """
    Replay-verify a past execution by its trace hash.

    Pipeline:
      1. Fetch artifact from external Bucket by trace_hash
      2. Verify artifact_hash integrity
      3. Reconstruct EvaluateActionRequest from stored payload
      4. Re-evaluate through Sarathi
      5. Compare decisions for byte-identical match

    Returns ReplayResult on success, None if artifact not found.
    """
    return verify_by_trace_hash(trace_hash)


def verify_bucket_entry(artifact: Dict[str, Any]) -> ReplayResult:
    """
    Replay-verify a single bucket artifact from the external Bucket Service.
    """
    execution_id = artifact.get("artifact_id", "UNKNOWN")
    payload = artifact.get("payload", {})

    trace_hash = payload.get("trace_hash", "UNKNOWN")
    original_decision = payload.get("decision", "UNKNOWN")
    original_risk_score = payload.get("risk_score", 0.0)

    # Step 1: Verify replay proof / artifact hash
    recomputed_hash = compute_artifact_hash(artifact)
    stored_hash = artifact.get("artifact_hash", "")
    replay_proof_valid = recomputed_hash == stored_hash

    if not replay_proof_valid:
        logger.warning(
            f"Artifact hash mismatch for execution {execution_id}",
            extra={
                "event_type": "replay_proof_invalid",
                "execution_id": execution_id,
            },
        )

    # Step 2: Reconstruct EvaluateActionRequest
    request_payload = payload.get("request_payload")
    if not request_payload:
        return ReplayResult(
            bucket_id=execution_id,
            trace_hash=trace_hash,
            original_decision=original_decision,
            replayed_decision="ERROR",
            original_risk_score=original_risk_score,
            replayed_risk_score=0.0,
            match=False,
            replay_proof_valid=replay_proof_valid,
            error="Missing request_payload in artifact",
        )

    try:
        request = EvaluateActionRequest(**request_payload)
    except Exception as e:
        return ReplayResult(
            bucket_id=execution_id,
            trace_hash=trace_hash,
            original_decision=original_decision,
            replayed_decision="ERROR",
            original_risk_score=original_risk_score,
            replayed_risk_score=0.0,
            match=False,
            replay_proof_valid=replay_proof_valid,
            error=f"Failed to reconstruct request: {str(e)}",
        )

    # Step 3: Re-evaluate through Sarathi
    try:
        replayed_response = evaluate_action(request)
    except Exception as e:
        return ReplayResult(
            bucket_id=execution_id,
            trace_hash=trace_hash,
            original_decision=original_decision,
            replayed_decision="ERROR",
            original_risk_score=original_risk_score,
            replayed_risk_score=0.0,
            match=False,
            replay_proof_valid=replay_proof_valid,
            error=f"Replay evaluation failed: {str(e)}",
        )

    # Step 4: Compare decisions
    replayed_decision = replayed_response.sarathi_decision.value
    match = (
        original_decision == replayed_decision
        and original_risk_score == replayed_response.risk_score
        and trace_hash == replayed_response.trace_hash
    )

    result = ReplayResult(
        bucket_id=execution_id,
        trace_hash=trace_hash,
        original_decision=original_decision,
        replayed_decision=replayed_decision,
        original_risk_score=original_risk_score,
        replayed_risk_score=replayed_response.risk_score,
        match=match,
        replay_proof_valid=replay_proof_valid,
        error=None,
    )

    logger.info(
        f"Replay verification: {'PASS' if match else 'FAIL'} | execution_id={execution_id}",
        extra={
            "event_type": "replay_verification",
            "execution_id": execution_id,
            "match": match,
            "replay_proof_valid": replay_proof_valid,
        },
    )

    return result


def verify_all() -> List[ReplayResult]:
    """Replay-verify ALL entries fetched from the external Bucket."""
    entries = get_bucket_entries()
    results = []
    if isinstance(entries, dict) and "items" in entries:
        entries = entries["items"]
    elif isinstance(entries, dict) and "artifacts" in entries:
        entries = entries["artifacts"]

    for entry in entries:
        result = verify_bucket_entry(entry)
        results.append(result)
    return results


def verify_by_trace_hash(trace_hash: str) -> Optional[ReplayResult]:
    """
    Search external Bucket for an artifact matching the trace_hash
    and replay-verify it.
    """
    entries = get_bucket_entries()
    if isinstance(entries, dict) and "artifacts" in entries:
        entries = entries["artifacts"]
    elif isinstance(entries, dict) and "items" in entries:
        entries = entries["items"]

    for entry in entries:
        payload = entry.get("payload", {})
        if payload.get("trace_hash") == trace_hash or entry.get("artifact_id") == trace_hash:
            return verify_bucket_entry(entry)

    return None


# ============================================================
# Enforcement Ledger — Thin facade backed by external Bucket
# ============================================================
# The in-memory ledger is retained ONLY for test compatibility.
# In production, all persistence is via write_execution_record().

import threading
from app.enforcement_schemas import SarathiEvaluateResponse


@dataclass(frozen=True)
class EnforcementLedgerEntry:
    """A single, immutable enforcement decision record."""
    execution_id: str
    trace_hash: str
    timestamp_utc: str
    request_payload: Dict[str, Any]
    dgic_snapshot: Dict[str, Any]
    decision: str
    risk_score: float
    confidence: float
    failure_reason: str | None


class _EnforcementLedger:
    """
    Thin in-memory ledger that also writes to external Bucket.
    The in-memory portion exists for test replay; production
    truth-of-record is the external Bucket service.
    """
    def __init__(self):
        self._entries: List[EnforcementLedgerEntry] = []
        self._lock = threading.RLock()

    def record(
        self,
        execution_id: str,
        timestamp_utc: str,
        request: EvaluateActionRequest,
        sarathi_response: SarathiEvaluateResponse,
    ) -> EnforcementLedgerEntry:
        # EXECUTION ID GUARD (Phase 6)
        if request.execution_id != execution_id:
            logger.error(
                f"Bucket ledger: execution_id mismatch | caller={execution_id} request={request.execution_id}",
                extra={"event_type": "bucket_execution_id_mismatch"},
            )
        if sarathi_response.execution_id != execution_id:
            logger.error(
                f"Bucket ledger: execution_id mismatch | caller={execution_id} sarathi={sarathi_response.execution_id}",
                extra={"event_type": "bucket_execution_id_mismatch"},
            )

        request_dump = request.model_dump(mode="json")

        entry = EnforcementLedgerEntry(
            execution_id=execution_id,
            trace_hash=sarathi_response.trace_hash,
            timestamp_utc=timestamp_utc,
            request_payload=request_dump,
            dgic_snapshot={},
            decision=sarathi_response.sarathi_decision.value,
            risk_score=sarathi_response.risk_score,
            confidence=sarathi_response.confidence,
            failure_reason=sarathi_response.failure_reason,
        )

        with self._lock:
            self._entries.append(entry)

        # Also persist to external Bucket
        write_execution_record(
            execution_id=execution_id,
            decision=entry.decision,
            risk_score=entry.risk_score,
            confidence=entry.confidence,
            trace_hash=entry.trace_hash,
            request_payload=request_dump,
            failure_reason=entry.failure_reason,
        )

        logger.debug(
            f"Ledger entry recorded | trace_hash={entry.trace_hash[:8]}...",
            extra={
                "event_type": "ledger_record",
                "execution_id": entry.execution_id,
                "decision": entry.decision,
            },
        )
        return entry

    def get_all(self) -> List[EnforcementLedgerEntry]:
        with self._lock:
            return list(self._entries)

    def get_by_trace_hash(self, trace_hash: str) -> EnforcementLedgerEntry | None:
        with self._lock:
            for entry in self._entries:
                if entry.trace_hash == trace_hash:
                    return entry
        return None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


ledger_instance = _EnforcementLedger()


def record_decision(
    execution_id: str,
    timestamp_utc: str,
    request: EvaluateActionRequest,
    sarathi_response: SarathiEvaluateResponse,
) -> EnforcementLedgerEntry:
    return ledger_instance.record(execution_id, timestamp_utc, request, sarathi_response)


def get_ledger_entries() -> List[EnforcementLedgerEntry]:
    return ledger_instance.get_all()


def get_ledger_entry(trace_hash: str) -> EnforcementLedgerEntry | None:
    return ledger_instance.get_by_trace_hash(trace_hash)


def clear_ledger() -> None:
    ledger_instance.clear()
