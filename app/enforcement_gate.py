"""
Enforcement Gate — Layer 4 Execution Gate
============================================
The pure execution gate that enforces Sarathi-approved decisions.

This module does NOT make decisions. It receives the authoritative
SarathiEvaluateResponse and:
  1. Validates the Sarathi decision is present and structurally sound
  2. Records the decision to the enforcement ledger
  3. Writes the decision to the persistent bucket ledger
  4. Returns an ExecuteActionResponse confirming enforcement

Authority Boundary (IMMUTABLE):
  - This module NEVER evaluates risk, thresholds, or epistemic states.
  - All decision authority belongs to Sarathi (Layer 1).
  - This module ONLY executes Sarathi-approved decisions.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.enforcement_schemas import (
    EvaluateActionRequest,
    SarathiEvaluateResponse,
    SarathiDecision,
    EnforcementDecision,
    ExecuteActionRequest,
    ExecuteActionResponse,
    SourceSystem,
)
from app.enforcement_ledger import record_decision
from app.bucket_ledger import write_bucket_entry

logger = logging.getLogger(__name__)


# ============================================================
# Sarathi → Enforcement Decision Mapping
# ============================================================

def _map_sarathi_to_enforcement(sarathi_decision: SarathiDecision) -> EnforcementDecision:
    """
    Deterministic 1:1 mapping from Sarathi governance decision
    to enforcement gate disposition.

    Sarathi ALLOW  → Enforcement ALLOW
    Sarathi DENY   → Enforcement DENY
    Sarathi ABSTAIN → Enforcement ABSTAIN
    """
    return EnforcementDecision(sarathi_decision.value)


# ============================================================
# Enforcement Execution
# ============================================================

def enforce_decision(
    request: EvaluateActionRequest,
    sarathi_response: SarathiEvaluateResponse,
    dgic_snapshot_dict: Optional[dict] = None,
) -> ExecuteActionResponse:
    """
    Enforce a Sarathi-approved decision.

    Pipeline:
      1. Map Sarathi decision to enforcement disposition
      2. Record to enforcement ledger
      3. Write to persistent bucket ledger
      4. Return ExecuteActionResponse

    This function NEVER evaluates risk. It only enforces.
    """
    execution_id = request.execution_id
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Enforcement gate: enforcing Sarathi decision",
        extra={
            "execution_id": execution_id,
            "event_type": "enforcement_enforce_start",
            "sarathi_decision": sarathi_response.sarathi_decision.value,
            "source_system": request.source_system.value,
        },
    )

    # Step 1: Map Sarathi → Enforcement
    enforcement_decision = _map_sarathi_to_enforcement(sarathi_response.sarathi_decision)
    executed = enforcement_decision == EnforcementDecision.ALLOW

    # Step 2: Record to enforcement ledger
    record_decision(
        execution_id=execution_id,
        timestamp_utc=timestamp_utc,
        request=request,
        sarathi_response=sarathi_response,
    )

    # Step 3: Write to persistent bucket ledger
    write_bucket_entry(
        execution_id=execution_id,
        request_payload=request.model_dump(mode="json"),
        dgic_snapshot=dgic_snapshot_dict or {},
        decision=enforcement_decision.value,
        risk_score=sarathi_response.risk_score,
        confidence=sarathi_response.confidence,
        failure_reason=sarathi_response.failure_reason,
        trace_hash=sarathi_response.trace_hash,
    )

    # Step 4: Build response
    response = ExecuteActionResponse(
        execution_id=execution_id,
        enforcement_decision=enforcement_decision,
        executed=executed,
        trace_hash=sarathi_response.trace_hash,
    )

    logger.info(
        f"Enforcement gate: {enforcement_decision.value} | executed={executed}",
        extra={
            "execution_id": execution_id,
            "event_type": "enforcement_enforce_complete",
            "enforcement_decision": enforcement_decision.value,
            "sarathi_decision": sarathi_response.sarathi_decision.value,
            "executed": executed,
            "risk_score": sarathi_response.risk_score,
            "trace_hash": sarathi_response.trace_hash,
        },
    )

    return response
