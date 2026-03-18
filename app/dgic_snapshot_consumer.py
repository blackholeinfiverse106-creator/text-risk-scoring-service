"""
DGIC Snapshot Consumer
=======================
Formal ingestion, verification, and freezing of DGIC epistemic state snapshots.

This module is the ONLY entry point through which DGIC state enters enforcement.
All snapshots are frozen at ingestion — enforcement NEVER mutates upstream state.

Invariants (IMMUTABLE):
  - Snapshots are frozen (immutable) after ingestion.
  - Cryptographic seal is verified at ingestion time.
  - Snapshot hash is computed at ingestion and verified post-processing.
  - Entropy boundaries are classified at ingestion.
  - No field of the snapshot may be written to after ingestion.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from app.dgic_adapter import (
    DGICInput,
    DGICPayload,
    EpistemicState,
    validate_dgic_input,
    compute_envelope_hash,
    DGICContractViolation,
)

logger = logging.getLogger(__name__)


# ============================================================
# Entropy Boundary Classification
# ============================================================

class EntropyBoundary(str, Enum):
    """
    Deterministic entropy zone classification.

    STABLE   — Low entropy. Full confidence in epistemic grounding.
    ELEVATED — Moderate entropy. Confidence degraded, extra caution warranted.
    CRITICAL — High entropy. Maximum caution. Signal reliability severely compromised.
    """
    STABLE = "STABLE"
    ELEVATED = "ELEVATED"
    CRITICAL = "CRITICAL"


# Entropy threshold constants
ENTROPY_STABLE_CEILING = 0.3
ENTROPY_ELEVATED_CEILING = 0.7


def classify_entropy_boundary(entropy_score: float) -> EntropyBoundary:
    """
    Deterministically classify entropy into a boundary zone.

    [0.0, 0.3) → STABLE
    [0.3, 0.7) → ELEVATED
    [0.7, 1.0] → CRITICAL
    """
    if entropy_score < ENTROPY_STABLE_CEILING:
        return EntropyBoundary.STABLE
    elif entropy_score < ENTROPY_ELEVATED_CEILING:
        return EntropyBoundary.ELEVATED
    else:
        return EntropyBoundary.CRITICAL


# ============================================================
# DGIC Snapshot — Frozen at Ingestion
# ============================================================

@dataclass(frozen=True)
class DGICSnapshot:
    """
    An ingested and frozen DGIC epistemic state snapshot.

    All fields are set at ingestion and CANNOT be modified.
    The snapshot_hash is the cryptographic proof that enforcement
    did not mutate the DGIC state during processing.
    """
    snapshot_id: str
    ingested_at: str  # ISO-8601 UTC timestamp
    dgic_input: DGICInput  # The frozen DGIC envelope
    snapshot_hash: str  # SHA-256 of the snapshot at ingestion
    entropy_boundary: EntropyBoundary
    verified: bool  # True if cryptographic seal passed at ingestion


# ============================================================
# Snapshot Hash Computation
# ============================================================

def _compute_snapshot_hash(
    snapshot_id: str,
    ingested_at: str,
    dgic_input: DGICInput,
    entropy_boundary: EntropyBoundary,
) -> str:
    """
    Compute a deterministic SHA-256 hash of the entire snapshot state.
    Used to verify immutability: hash at ingestion == hash post-processing.
    """
    canonical = {
        "snapshot_id": snapshot_id,
        "ingested_at": ingested_at,
        "version": dgic_input.version,
        "lineage_hash": dgic_input.lineage_hash,
        "envelope_hash": dgic_input.envelope_hash,
        "epistemic_state": dgic_input.payload.epistemic_state.value,
        "entropy_score": dgic_input.payload.entropy_score,
        "contradiction_flag": dgic_input.payload.contradiction_flag,
        "collapse_flag": dgic_input.collapse_flag,
        "entropy_boundary": entropy_boundary.value,
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ============================================================
# Snapshot Ingestion
# ============================================================

class DGICSnapshotError(Exception):
    """Raised when DGIC snapshot ingestion or verification fails."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def ingest_dgic_snapshot(
    epistemic_state: str,
    entropy_score: float,
    contradiction_flag: bool,
    lineage_hash: str,
    envelope_hash: str,
    snapshot_id: Optional[str] = None,
    ingestion_timestamp: Optional[str] = None,
) -> DGICSnapshot:
    """
    Formally ingest a DGIC epistemic state into a frozen snapshot.

    Pipeline:
      1. Parse raw fields into DGICInput (frozen dataclass)
      2. Validate cryptographic envelope seal
      3. Classify entropy boundary
      4. Compute snapshot hash at point of ingestion
      5. Return frozen DGICSnapshot — immutable from here forward

    Raises DGICSnapshotError on any validation failure.
    """
    # Generate snapshot metadata
    sid = snapshot_id or str(uuid.uuid4())
    ts = ingestion_timestamp or datetime.now(timezone.utc).isoformat()

    # Step 1: Parse into frozen DGICInput
    try:
        state_enum = EpistemicState(epistemic_state)
    except ValueError:
        raise DGICSnapshotError(
            "INVALID_EPISTEMIC_STATE",
            f"Invalid epistemic state: '{epistemic_state}'. Must be one of: KNOWN, INFERRED, AMBIGUOUS, UNKNOWN"
        )

    payload = DGICPayload(
        epistemic_state=state_enum,
        entropy_score=entropy_score,
        contradiction_flag=contradiction_flag,
    )

    dgic_input = DGICInput(
        version="schema_v1",
        lineage_hash=lineage_hash,
        envelope_hash=envelope_hash,
        payload=payload,
        collapse_flag=False,  # Enforcement NEVER collapses epistemic state
    )

    # Step 2: Validate cryptographic envelope seal
    verified = False
    try:
        validate_dgic_input(dgic_input)
        verified = True
    except DGICContractViolation as e:
        raise DGICSnapshotError(
            "DGIC_SEAL_VERIFICATION_FAILED",
            f"Cryptographic seal verification failed: {str(e)}"
        )

    # Step 3: Classify entropy boundary
    entropy_boundary = classify_entropy_boundary(entropy_score)

    # Step 4: Compute snapshot hash
    snapshot_hash = _compute_snapshot_hash(sid, ts, dgic_input, entropy_boundary)

    # Step 5: Construct frozen snapshot
    snapshot = DGICSnapshot(
        snapshot_id=sid,
        ingested_at=ts,
        dgic_input=dgic_input,
        snapshot_hash=snapshot_hash,
        entropy_boundary=entropy_boundary,
        verified=verified,
    )

    logger.info(
        "DGIC snapshot ingested",
        extra={
            "event_type": "dgic_snapshot_ingested",
            "snapshot_id": sid,
            "epistemic_state": epistemic_state,
            "entropy_score": entropy_score,
            "entropy_boundary": entropy_boundary.value,
            "contradiction_flag": contradiction_flag,
            "verified": verified,
            "snapshot_hash": snapshot_hash[:16] + "...",
        },
    )

    return snapshot


# ============================================================
# Post-Processing Integrity Verification
# ============================================================

def verify_snapshot_integrity(snapshot: DGICSnapshot) -> bool:
    """
    Verify that the snapshot was NOT mutated during enforcement processing.

    Recomputes the snapshot hash from current field values and compares
    to the hash recorded at ingestion time.

    Returns True if integrity holds. Raises DGICSnapshotError if violated.
    """
    recomputed = _compute_snapshot_hash(
        snapshot.snapshot_id,
        snapshot.ingested_at,
        snapshot.dgic_input,
        snapshot.entropy_boundary,
    )

    if recomputed != snapshot.snapshot_hash:
        logger.error(
            "DGIC snapshot integrity violation detected!",
            extra={
                "event_type": "dgic_snapshot_integrity_violation",
                "snapshot_id": snapshot.snapshot_id,
                "expected_hash": snapshot.snapshot_hash,
                "recomputed_hash": recomputed,
            },
        )
        raise DGICSnapshotError(
            "SNAPSHOT_INTEGRITY_VIOLATION",
            f"Snapshot {snapshot.snapshot_id} was mutated during processing. "
            f"Expected hash: {snapshot.snapshot_hash[:16]}..., "
            f"got: {recomputed[:16]}..."
        )

    logger.debug(
        "DGIC snapshot integrity verified",
        extra={
            "event_type": "dgic_snapshot_integrity_verified",
            "snapshot_id": snapshot.snapshot_id,
        },
    )

    return True


# ============================================================
# Snapshot Serialization (for replay ledger)
# ============================================================

def snapshot_to_dict(snapshot: DGICSnapshot) -> dict:
    """
    Serialize a DGICSnapshot to a plain dict for JSON storage / replay.
    """
    return {
        "snapshot_id": snapshot.snapshot_id,
        "ingested_at": snapshot.ingested_at,
        "version": snapshot.dgic_input.version,
        "lineage_hash": snapshot.dgic_input.lineage_hash,
        "envelope_hash": snapshot.dgic_input.envelope_hash,
        "epistemic_state": snapshot.dgic_input.payload.epistemic_state.value,
        "entropy_score": snapshot.dgic_input.payload.entropy_score,
        "contradiction_flag": snapshot.dgic_input.payload.contradiction_flag,
        "collapse_flag": snapshot.dgic_input.collapse_flag,
        "entropy_boundary": snapshot.entropy_boundary.value,
        "snapshot_hash": snapshot.snapshot_hash,
        "verified": snapshot.verified,
    }
