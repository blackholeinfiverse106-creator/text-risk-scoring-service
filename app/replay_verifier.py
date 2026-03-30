"""
Replay Verifier
================
Deterministic replay verification tool for the enforcement bucket ledger.

Re-evaluates historical enforcement decisions using the stored request payload
from the external Primary_Bucket_Owner service and verifies that the output 
is byte-identical to the original decision.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from app.bucket_ledger import (
    compute_artifact_hash,
    get_bucket_entries,
    get_bucket_entry,
)
from app.enforcement_schemas import EvaluateActionRequest
from app.sarathi_governance import evaluate_action

logger = logging.getLogger(__name__)


# ============================================================
# Replay Result
# ============================================================

@dataclass(frozen=True)
class ReplayResult:
    """
    Result of replaying a single bucket entry (artifact).
    """
    bucket_id: str           # Actually execution_id now
    trace_hash: str
    original_decision: str
    replayed_decision: str
    original_risk_score: float
    replayed_risk_score: float
    match: bool              # True if decisions are byte-identical
    replay_proof_valid: bool  # True if stored artifact_hash matches recomputed
    error: Optional[str]     # None if no error occurred


# ============================================================
# Single Entry Verification
# ============================================================

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

    # Step 3: Re-evaluate through enforcement gate
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


# ============================================================
# Full Ledger Verification
# ============================================================

def verify_all() -> List[ReplayResult]:
    """
    Replay-verify ALL entries fetched from the external Bucket.
    """
    entries = get_bucket_entries()
    results = []
    # Currently get_bucket_entries returns a list of artifacts OR {"artifacts": [...]} depending on schema
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
    We don't natively index by trace_hash in external bucket (indexed by artifact_id).
    We must scan for trace_hash match or assume trace_hash == artifact_id 
    in the new routing model.
    """
    # Just fall back to scanning if not found
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
