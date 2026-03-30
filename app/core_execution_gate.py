"""
Core Execution Gate
====================
Connects the Sarathi governance engine with the enforcement execution gate.

Core submits action proposals through this module.
The module evaluates each proposal via Sarathi (Layer 1 governance),
maps the governance decision to Core-specific outputs, and executes
only if the decision is ALLOW.

Core Execution Flow:
  1. Core submits a CoreActionProposal
  2. Proposal is converted to EvaluateActionRequest
  3. Sarathi evaluates the proposal (governance decision)
  4. Enforcement gate records the decision (execution gate)
  5. Sarathi decision is mapped to Core output
  6. Execution occurs ONLY if decision = ALLOW

All decisions are deterministic and logged.
"""

from __future__ import annotations

import logging
from typing import Optional
from pydantic import BaseModel, Field

from app.enforcement_schemas import (
    EvaluateActionRequest,
    SarathiEvaluateResponse,
    SarathiDecision,
    EnforcementDecision,
    ContextSignal,
    DGICEpistemicStateInput,
    SourceSystem,
)
from app.sarathi_governance import evaluate_action as sarathi_evaluate
from app.enforcement_gate import enforce_decision

logger = logging.getLogger(__name__)


# ============================================================
# Sarathi Decision → Core Decision Mapping
# ============================================================

# Deterministic mapping from Sarathi failure reasons to Core outputs
_AMBIGUOUS_KEYWORDS = {"ambiguous", "epistemic uncertainty"}
_UNKNOWN_KEYWORDS = {"abstention", "unknown", "no grounded evidence"}
_SEAL_KEYWORDS = {"snapshot rejected", "seal", "contract violation", "tampered"}


def _map_to_core_decision(
    sarathi_decision: SarathiDecision,
    failure_reason: Optional[str],
) -> EnforcementDecision:
    """
    Map a Sarathi governance decision to a Core-specific execution decision.

    Mapping rules (deterministic, evaluated in order):
      ALLOW                           → ALLOW (execute)
      DENY  + high risk               → BLOCK
      DENY  + AMBIGUOUS epistemic     → ESCALATE
      DENY  + CRITICAL entropy        → BLOCK
      ABSTAIN + UNKNOWN state         → REQUEST_MORE_DATA
      ABSTAIN + seal verification     → BLOCK
      Any other DENY                  → BLOCK (fail-safe)
      Any other ABSTAIN               → REQUEST_MORE_DATA (fail-safe)
    """
    if sarathi_decision == SarathiDecision.ALLOW:
        return EnforcementDecision.ALLOW

    reason_lower = (failure_reason or "").lower()

    if sarathi_decision == SarathiDecision.ABSTAIN:
        # Seal failures → hard block
        if any(kw in reason_lower for kw in _SEAL_KEYWORDS):
            return EnforcementDecision.BLOCK
        # Everything else (UNKNOWN state, etc.) → request more data
        return EnforcementDecision.REQUEST_MORE_DATA

    if sarathi_decision == SarathiDecision.DENY:
        # Ambiguous epistemic state → escalate for human review
        if any(kw in reason_lower for kw in _AMBIGUOUS_KEYWORDS):
            return EnforcementDecision.ESCALATE
        # All other denials → hard block
        return EnforcementDecision.BLOCK

    # Fallback (should never reach here)
    return EnforcementDecision.BLOCK


# ============================================================
# Core Execution Result
# ============================================================

class CoreExecutionResult(BaseModel):
    """
    The result of submitting an action proposal to the Core execution gate.

    `executed` is True ONLY when execution_decision == ALLOW.
    """
    execution_id: str = Field(
        ..., description="The original execution ID"
    )
    execution_decision: EnforcementDecision = Field(
        ..., description="ALLOW, BLOCK, ESCALATE, or REQUEST_MORE_DATA"
    )
    executed: bool = Field(
        ..., description="True only if execution_decision == ALLOW"
    )
    risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Final computed risk score"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Decision confidence"
    )
    failure_reason: Optional[str] = Field(
        None, description="Null on ALLOW. Structured reason on BLOCK/ESCALATE/REQUEST_MORE_DATA."
    )
    trace_hash: str = Field(
        ..., min_length=64, max_length=64,
        description="SHA-256 trace hash for deterministic replay"
    )
    gate_decision: EnforcementDecision = Field(
        ..., description="The raw Sarathi governance decision before Core mapping"
    )


# ============================================================
# Core Submission Pipeline
# ============================================================

def submit_proposal(
    execution_id: str,
    actor: str,
    proposed_action: str,
    context_signals: list,
    dgic_epistemic_state: DGICEpistemicStateInput,
    source_system: SourceSystem,
) -> CoreExecutionResult:
    """
    Submit an action proposal to the Core execution gate.

    Pipeline:
      1. Build EvaluateActionRequest from proposal fields
      2. Sarathi evaluates the proposal (governance decision)
      3. Enforcement gate records the decision (execution)
      4. Map Sarathi decision to Core output
      5. Set executed = True ONLY if ALLOW
      6. Log and return CoreExecutionResult
    """
    logger.info(
        f"Core proposal submitted | execution_id={execution_id}",
        extra={
            "event_type": "core_proposal_submitted",
            "execution_id": execution_id,
            "actor": actor,
            "source_system": source_system.value,
        },
    )

    # Step 1: Convert to enforcement request
    request = EvaluateActionRequest(
        execution_id=execution_id,
        actor=actor,
        proposed_action=proposed_action,
        context_signals=context_signals,
        dgic_epistemic_state=dgic_epistemic_state,
        source_system=source_system,
    )

    # Step 2: Sarathi governance evaluation (Layer 1 — decision authority)
    sarathi_response: SarathiEvaluateResponse = sarathi_evaluate(request)

    # Step 3: Enforcement gate records the decision (Layer 4 — execution)
    enforce_decision(request, sarathi_response)

    # Step 4: Map Sarathi decision to Core output
    core_decision = _map_to_core_decision(
        sarathi_response.sarathi_decision,
        sarathi_response.failure_reason,
    )

    # Map raw Sarathi decision to EnforcementDecision for gate_decision field
    raw_gate = EnforcementDecision(sarathi_response.sarathi_decision.value)

    # Step 5: Execute only if ALLOW
    executed = core_decision == EnforcementDecision.ALLOW

    # Step 6: Build result
    result = CoreExecutionResult(
        execution_id=execution_id,
        execution_decision=core_decision,
        executed=executed,
        risk_score=sarathi_response.risk_score,
        confidence=sarathi_response.confidence,
        failure_reason=sarathi_response.failure_reason,
        trace_hash=sarathi_response.trace_hash,
        gate_decision=raw_gate,
    )

    logger.info(
        f"Core execution result: {core_decision.value} | executed={executed}",
        extra={
            "event_type": "core_execution_result",
            "execution_id": execution_id,
            "sarathi_decision": sarathi_response.sarathi_decision.value,
            "core_decision": core_decision.value,
            "executed": executed,
            "risk_score": sarathi_response.risk_score,
            "trace_hash": sarathi_response.trace_hash,
        },
    )

    return result
