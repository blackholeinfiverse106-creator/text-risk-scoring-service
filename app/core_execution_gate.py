"""
Core Execution Gate
====================
Connects the enforcement gateway with the Core execution pipeline.

Core submits action proposals through this module.
The module evaluates each proposal via the enforcement gate,
maps the gate decision to Core-specific outputs, and executes
only if the decision is ALLOW.

Core Execution Flow:
  1. Core submits a CoreActionProposal
  2. Proposal is converted to EvaluateActionRequest
  3. Enforcement gate evaluates deterministically
  4. Gate decision is mapped to Core output
  5. Execution occurs ONLY if decision = ALLOW
  6. Decision is logged to the enforcement ledger

All decisions are deterministic and logged.
"""

from __future__ import annotations

import logging
from typing import Optional
from pydantic import BaseModel, Field

from app.enforcement_schemas import (
    EvaluateActionRequest,
    EvaluateActionResponse,
    EnforcementDecision,
    ContextSignal,
    DGICEpistemicStateInput,
    SourceSystem,
)
from app.enforcement_gate import evaluate_action

logger = logging.getLogger(__name__)


# ============================================================
# Core Decision Mapping
# ============================================================

# Gate decisions that mean "execute"
_EXECUTE_DECISIONS = {EnforcementDecision.ALLOW}

# Deterministic mapping from gate failure reasons to Core outputs
_AMBIGUOUS_KEYWORDS = {"ambiguous", "epistemic uncertainty"}
_UNKNOWN_KEYWORDS = {"abstention", "unknown", "no grounded evidence"}
_SEAL_KEYWORDS = {"snapshot rejected", "seal", "contract violation", "tampered"}


def _map_to_core_decision(
    gate_decision: EnforcementDecision,
    failure_reason: Optional[str],
) -> EnforcementDecision:
    """
    Map an enforcement gate decision to a Core-specific execution decision.

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
    if gate_decision == EnforcementDecision.ALLOW:
        return EnforcementDecision.ALLOW

    reason_lower = (failure_reason or "").lower()

    if gate_decision == EnforcementDecision.ABSTAIN:
        # Seal failures → hard block
        if any(kw in reason_lower for kw in _SEAL_KEYWORDS):
            return EnforcementDecision.BLOCK
        # Everything else (UNKNOWN state, etc.) → request more data
        return EnforcementDecision.REQUEST_MORE_DATA

    if gate_decision == EnforcementDecision.DENY:
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
    proposal_id: str = Field(
        ..., description="The original proposal ID"
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
        ..., description="The raw enforcement gate decision before Core mapping"
    )


# ============================================================
# Core Submission Pipeline
# ============================================================

def submit_proposal(
    proposal_id: str,
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
      2. Evaluate via enforcement gate (deterministic)
      3. Map gate decision to Core output
      4. Set executed = True ONLY if ALLOW
      5. Log and return CoreExecutionResult
    """
    logger.info(
        f"Core proposal submitted | proposal_id={proposal_id}",
        extra={
            "event_type": "core_proposal_submitted",
            "proposal_id": proposal_id,
            "actor": actor,
            "source_system": source_system.value,
        },
    )

    # Step 1: Convert to enforcement request
    request = EvaluateActionRequest(
        action_id=proposal_id,
        actor=actor,
        proposed_action=proposed_action,
        context_signals=context_signals,
        dgic_epistemic_state=dgic_epistemic_state,
        source_system=source_system,
    )

    # Step 2: Evaluate via enforcement gate
    gate_response: EvaluateActionResponse = evaluate_action(request)

    # Step 3: Map gate decision to Core output
    core_decision = _map_to_core_decision(
        gate_response.enforcement_decision,
        gate_response.failure_reason,
    )

    # Step 4: Execute only if ALLOW
    executed = core_decision == EnforcementDecision.ALLOW

    # Step 5: Build result
    result = CoreExecutionResult(
        proposal_id=proposal_id,
        execution_decision=core_decision,
        executed=executed,
        risk_score=gate_response.risk_score,
        confidence=gate_response.confidence,
        failure_reason=gate_response.failure_reason,
        trace_hash=gate_response.trace_hash,
        gate_decision=gate_response.enforcement_decision,
    )

    logger.info(
        f"Core execution result: {core_decision.value} | executed={executed}",
        extra={
            "event_type": "core_execution_result",
            "proposal_id": proposal_id,
            "gate_decision": gate_response.enforcement_decision.value,
            "core_decision": core_decision.value,
            "executed": executed,
            "risk_score": gate_response.risk_score,
            "trace_hash": gate_response.trace_hash,
        },
    )

    return result
