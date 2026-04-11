from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, Field

from app.enforcement_schemas import (
    EnforcementDecision,
)
from app.layer5_bucket import write_execution_record
from app.execution_controller import execute_action, block_execution
from app.rajya_validation_engine import RajyaValidationResult

logger = logging.getLogger(__name__)

class MandalaInvocationResult(BaseModel):
    execution_id: str = Field(..., description="The original execution ID")
    enforcement_decision: EnforcementDecision = Field(..., description="ALLOW | DENY | ABSTAIN")
    risk_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    trace_hash: str = Field(..., min_length=64, max_length=64)
    failure_reason: Optional[str] = Field(None)

def execute_core_mandala(
    execution_id: str,
    proposed_action: str,
    rajya_result: RajyaValidationResult,
    sarathi_risk_score: float,
    sarathi_confidence: float,
    sarathi_trace_hash: str,
    sarathi_failure_reason: Optional[str],
    request_payload: dict,
    dgic_snapshot_dict: dict
) -> MandalaInvocationResult:
    """
    Core Execution Layer — Pure Execution Only.

    Core does NOT:
      - Check Sarathi decisions
      - Check Enforcement verdicts
      - Perform any final decision validation

    Core receives RAJYA's verdict and acts on it:
      - EXECUTION_APPROVED → execute_action()
      - Anything else → block_execution()

    No intelligence. No governance. No validation. Execution only.
    """

    # ── PROOF LOG: Core execution entry ──
    logger.info(
        f"CORE ENTRY | execution_id={execution_id} | rajya_result={rajya_result.value}",
        extra={
            "event_type": "core_execution_start",
            "execution_id": execution_id,
            "rajya_result": rajya_result.value,
        },
    )

    # ── Core Decision: RAJYA is the sole authority ──
    if rajya_result == RajyaValidationResult.EXECUTION_APPROVED:
        core_decision = EnforcementDecision.ALLOW
        final_failure_reason = None
        execute_action(proposed_action, execution_id)
        logger.info(
            f"CORE EXECUTED | execution_id={execution_id} | action='{proposed_action}' | rajya=EXECUTION_APPROVED",
            extra={
                "event_type": "core_action_executed_proof",
                "execution_id": execution_id,
                "rajya_result": rajya_result.value,
                "core_decision": core_decision.value,
            },
        )
    else:
        core_decision = EnforcementDecision.DENY
        final_failure_reason = sarathi_failure_reason or f"RAJYA did not approve execution: {rajya_result.value}"
        block_execution(proposed_action, execution_id, final_failure_reason)
        logger.warning(
            f"CORE BLOCKED | execution_id={execution_id} | action='{proposed_action}' | rajya={rajya_result.value}",
            extra={
                "event_type": "core_action_blocked_proof",
                "execution_id": execution_id,
                "rajya_result": rajya_result.value,
                "core_decision": core_decision.value,
                "failure_reason": final_failure_reason,
            },
        )

    write_execution_record(
        execution_id=execution_id,
        decision=core_decision.value,
        risk_score=sarathi_risk_score,
        confidence=sarathi_confidence,
        trace_hash=sarathi_trace_hash,
        request_payload=request_payload,
        dgic_snapshot=dgic_snapshot_dict,
        failure_reason=final_failure_reason,
    )

    result = MandalaInvocationResult(
        execution_id=execution_id,
        enforcement_decision=core_decision,
        risk_score=sarathi_risk_score,
        confidence=sarathi_confidence,
        trace_hash=sarathi_trace_hash,
        failure_reason=final_failure_reason,
    )

    # ── PROOF LOG: Core execution exit ──
    logger.info(
        f"CORE EXIT | execution_id={execution_id} | decision={core_decision.value} | rajya={rajya_result.value}",
        extra={
            "event_type": "core_execution_result",
            "execution_id": execution_id,
            "enforcement_decision": core_decision.value,
            "rajya_result": rajya_result.value,
            "risk_score": sarathi_risk_score,
            "trace_hash": sarathi_trace_hash,
        },
    )

    return result

from dataclasses import dataclass
from typing import Dict, Any, List

class CoreAdapterValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")

@dataclass(frozen=True)
class CoreEnforcementPayload:
    aggregate_risk_score: float
    aggregate_risk_category: str
    aggregate_confidence: float
    signal_count: int
    active_signal_count: int
    epistemic_confidence: float
    signal_lineage: str
    collapse_state: str
    truth_boundary_reference: str
    telemetry_signal_id: str
    telemetry_timestamp: str
    safety_metadata: dict
    errors: Optional[dict]

from app.layer3_dgic import DGICInput, DGICPayload, EpistemicState, validate_dgic_input, DGICContractViolation
from app.layer6_insightbridge import UnifiedSignal, SignalType, aggregate_unified_signals
from app.layer3_dgic import wrap_in_dgic_envelope
from app.layer6_insightbridge import emit_telemetry_event

VALID_SIGNAL_TYPES = {st.value for st in SignalType}
_SAFETY_METADATA = {"is_decision": False, "authority": "NONE", "actionable": False}

def process_for_core(signals_raw: List[Dict[str, Any]]) -> CoreEnforcementPayload:
    if not isinstance(signals_raw, list) or len(signals_raw) == 0:
        raise CoreAdapterValidationError("EMPTY_SIGNALS", "At least one signal is required")
    # Stubbed adapter logic to keep scope clean for exercise.
    return CoreEnforcementPayload(
        aggregate_risk_score=0.0,
        aggregate_risk_category="LOW",
        aggregate_confidence=1.0,
        signal_count=1,
        active_signal_count=1,
        epistemic_confidence=1.0,
        signal_lineage="none",
        collapse_state="uncollapsed",
        truth_boundary_reference="none",
        telemetry_signal_id="sig-001",
        telemetry_timestamp="2026",
        safety_metadata=dict(_SAFETY_METADATA),
        errors=None
    )

def payload_to_dict(payload: CoreEnforcementPayload) -> Dict[str, Any]:
    from dataclasses import asdict
    return asdict(payload)
