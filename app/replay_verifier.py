"""
Replay Verifier
================
Deterministic replay verification tool for the enforcement bucket ledger.

Re-evaluates historical enforcement decisions using the stored request payload
and verifies that the output is byte-identical to the original decision.

This proves:
  1. The enforcement gate is deterministic (same inputs → same output)
  2. The bucket entry was not tampered with (replay_proof check)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from app.bucket_ledger import (
    BucketEntry,
    compute_replay_proof,
    get_bucket_entries,
    get_bucket_entry,
)
from app.enforcement_schemas import EvaluateActionRequest, EnforcementDecision
from app.enforcement_gate import evaluate_action

logger = logging.getLogger(__name__)


# ============================================================
# Replay Result
# ============================================================

@dataclass(frozen=True)
class ReplayResult:
    """
    Result of replaying a single bucket entry.
    """
    bucket_id: str
    trace_hash: str
    original_decision: str
    replayed_decision: str
    original_risk_score: float
    replayed_risk_score: float
    match: bool              # True if decisions are byte-identical
    replay_proof_valid: bool  # True if stored replay_proof matches recomputed
    error: Optional[str]     # None if no error occurred


# ============================================================
# Single Entry Verification
# ============================================================

def verify_bucket_entry(entry: BucketEntry) -> ReplayResult:
    """
    Replay-verify a single bucket entry.

    Steps:
      1. Verify the replay_proof (tamper detection on the stored entry)
      2. Reconstruct the EvaluateActionRequest from stored payload
      3. Re-evaluate through the enforcement gate
      4. Compare original decision to replayed decision
    """
    # Step 1: Verify replay proof (tamper detection)
    entry_dict = {
        "bucket_id": entry.bucket_id,
        "action_id": entry.action_id,
        "timestamp_utc": entry.timestamp_utc,
        "input_snapshot_hash": entry.input_snapshot_hash,
        "request_payload": entry.request_payload,
        "dgic_snapshot": entry.dgic_snapshot,
        "decision": entry.decision,
        "risk_score": entry.risk_score,
        "confidence": entry.confidence,
        "failure_reason": entry.failure_reason,
        "trace_hash": entry.trace_hash,
        "trace_lineage": entry.trace_lineage,
    }
    recomputed_proof = compute_replay_proof(entry_dict)
    replay_proof_valid = recomputed_proof == entry.replay_proof

    if not replay_proof_valid:
        logger.warning(
            f"Replay proof INVALID for bucket {entry.bucket_id[:8]}...",
            extra={
                "event_type": "replay_proof_invalid",
                "bucket_id": entry.bucket_id,
            },
        )

    # Step 2: Reconstruct EvaluateActionRequest from stored payload
    try:
        request = EvaluateActionRequest(**entry.request_payload)
    except Exception as e:
        return ReplayResult(
            bucket_id=entry.bucket_id,
            trace_hash=entry.trace_hash,
            original_decision=entry.decision,
            replayed_decision="ERROR",
            original_risk_score=entry.risk_score,
            replayed_risk_score=0.0,
            match=False,
            replay_proof_valid=replay_proof_valid,
            error=f"Failed to reconstruct request: {str(e)}",
        )

    # Step 3: Re-evaluate through enforcement gate
    try:
        replayed_response = evaluate_action(request)
    except Exception as e:
        return ReplayResult(
            bucket_id=entry.bucket_id,
            trace_hash=entry.trace_hash,
            original_decision=entry.decision,
            replayed_decision="ERROR",
            original_risk_score=entry.risk_score,
            replayed_risk_score=0.0,
            match=False,
            replay_proof_valid=replay_proof_valid,
            error=f"Replay evaluation failed: {str(e)}",
        )

    # Step 4: Compare decisions
    replayed_decision = replayed_response.enforcement_decision.value
    match = (
        entry.decision == replayed_decision
        and entry.risk_score == replayed_response.risk_score
        and entry.trace_hash == replayed_response.trace_hash
    )

    result = ReplayResult(
        bucket_id=entry.bucket_id,
        trace_hash=entry.trace_hash,
        original_decision=entry.decision,
        replayed_decision=replayed_decision,
        original_risk_score=entry.risk_score,
        replayed_risk_score=replayed_response.risk_score,
        match=match,
        replay_proof_valid=replay_proof_valid,
        error=None,
    )

    logger.info(
        f"Replay verification: {'PASS' if match else 'FAIL'} | bucket={entry.bucket_id[:8]}...",
        extra={
            "event_type": "replay_verification",
            "bucket_id": entry.bucket_id,
            "match": match,
            "replay_proof_valid": replay_proof_valid,
            "original_decision": entry.decision,
            "replayed_decision": replayed_decision,
        },
    )

    return result


# ============================================================
# Full Ledger Verification
# ============================================================

def verify_all() -> List[ReplayResult]:
    """
    Replay-verify ALL entries in the bucket ledger.
    Returns a list of ReplayResults for each entry.
    """
    entries = get_bucket_entries()
    results = []
    for entry in entries:
        result = verify_bucket_entry(entry)
        results.append(result)
    return results


def verify_by_trace_hash(trace_hash: str) -> Optional[ReplayResult]:
    """
    Replay-verify a specific bucket entry by its trace hash.
    Returns None if not found.
    """
    entry = get_bucket_entry(trace_hash)
    if entry is None:
        return None
    return verify_bucket_entry(entry)
