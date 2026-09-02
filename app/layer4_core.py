from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, Field

from app.enforcement_schemas import (
    EnforcementDecision,
)
from app.layer5_bucket import write_execution_record
import dataclasses
from app.execution_controller import execute_action, block_execution
from app.rajya_validation_engine import RajyaValidationResult
from app.layer1_sarathi import SarathiEnforcementToken, enforce_token, SarathiHardBlockError
import requests

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
    enforcement_token: Optional[SarathiEnforcementToken],
    sarathi_risk_score: float,
    sarathi_confidence: float,
    sarathi_trace_hash: str,
    request_payload: dict,
    dgic_snapshot_dict: dict
) -> MandalaInvocationResult:
    """
    Core Execution Layer — Pure Execution Only.

    Core does NOT:
      - Check Sarathi decisions
      - Check Enforcement verdicts
      - Perform any final decision validation

    Core receives RAJYA's verdict AND passes the enforcement token through
    Sarathi's enforce_token() gate:
      - enforce_token() returns ALLOW → execute_action()
      - enforce_token() raises SarathiHardBlockError → block_execution()

    The enforcement token gate is the final authority.
    No intelligence. No governance. No decision logic. Execution only.
    """

    # ── PROOF LOG: Core execution entry ──
    logger.info(
        f"CORE ENTRY | execution_id={execution_id} | token_present={enforcement_token is not None}",
        extra={
            "event_type": "core_execution_start",
            "execution_id": execution_id,
            "token_present": enforcement_token is not None,
        },
    )

    # ── Sarathi Gate: enforce_token() is the sole authority ──
    try:
        gate_verdict = enforce_token(enforcement_token, pipeline_execution_id=execution_id)
    except SarathiHardBlockError as e:
        core_decision = EnforcementDecision.DENY
        final_failure_reason = f"Sarathi gate HARD BLOCK: {e.code} — {e.message}"
        block_execution(proposed_action, execution_id, final_failure_reason)
        logger.warning(
            f"CORE BLOCKED | execution_id={execution_id} | action='{proposed_action}' | sarathi_gate=BLOCK | code={e.code}",
            extra={
                "event_type": "core_action_blocked_proof",
                "execution_id": execution_id,
                "core_decision": core_decision.value,
                "sarathi_gate_code": e.code,
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

        logger.info(
            f"CORE EXIT | execution_id={execution_id} | decision={core_decision.value} | gate=BLOCK",
            extra={
                "event_type": "core_execution_result",
                "execution_id": execution_id,
                "enforcement_decision": core_decision.value,
                "sarathi_gate": "BLOCK",
            },
        )
        return result

    # ── Gate passed: ALLOW → execute ──
    core_decision = EnforcementDecision.ALLOW
    final_failure_reason = None
    
    import os
    import json
    
    # LIVE EXTERNAL INTEGRATION: Trigger execution on external Core Service
    core_url = os.environ.get("CORE_SERVICE_URL", "http://163.128.209.18:8004")
    endpoint = f"{core_url}/execute_task"
    
    payload = {
        "input": proposed_action,
        "agent": request_payload.get("actor", "marine-intelligence-bot"),
        "trace_id": execution_id,
        "execution_token": json.dumps(dataclasses.asdict(enforcement_token)) if enforcement_token else ""
    }
    
    try:
        response = requests.post(endpoint, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"External Core API Success | trace_id={execution_id} | response={response.text}")
        else:
            core_decision = EnforcementDecision.DENY
            final_failure_reason = f"External Core API failed with status {response.status_code}: {response.text}"
            logger.error(final_failure_reason)
    except Exception as e:
        core_decision = EnforcementDecision.DENY
        final_failure_reason = f"External Core API connection error: {str(e)}"
        logger.error(final_failure_reason)
    logger.info(
        f"CORE EXECUTED | execution_id={execution_id} | action='{proposed_action}' | sarathi_gate=ALLOW",
        extra={
            "event_type": "core_action_executed_proof",
            "execution_id": execution_id,
            "core_decision": core_decision.value,
            "sarathi_gate": gate_verdict,
            "token_signature": enforcement_token.signature_hash,
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
        f"CORE EXIT | execution_id={execution_id} | decision={core_decision.value} | sarathi_gate=ALLOW",
        extra={
            "event_type": "core_execution_result",
            "execution_id": execution_id,
            "enforcement_decision": core_decision.value,
            "risk_score": sarathi_risk_score,
            "trace_hash": sarathi_trace_hash,
            "sarathi_gate": "ALLOW",
            "token_signature": enforcement_token.signature_hash,
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
        
    import uuid
    execution_id = f"exec-{uuid.uuid4().hex[:12]}"

    unified_signals = []
    for idx, s in enumerate(signals_raw):
        try:
            dgic_dict = s.get("dgic_envelope", {})
            payload_dict = dgic_dict.get("payload", {})
            
            payload = DGICPayload(
                epistemic_state=EpistemicState(payload_dict.get("epistemic_state", "UNKNOWN")),
                entropy_score=float(payload_dict.get("entropy_score", 1.0)),
                contradiction_flag=bool(payload_dict.get("contradiction_flag", False))
            )
            
            dgic_input = DGICInput(
                version=dgic_dict.get("version", "schema_v1"),
                lineage_hash=dgic_dict.get("lineage_hash", "0"*64),
                envelope_hash=dgic_dict.get("envelope_hash", "0"*64),
                payload=payload,
                collapse_flag=bool(dgic_dict.get("collapse_flag", False))
            )
            
            sig = UnifiedSignal(
                signal_id=s.get("signal_id", f"sig-{idx}"),
                signal_type=SignalType(s.get("signal_type", "TEXT_RISK_SIGNAL")),
                base_risk_score=float(s.get("base_risk_score", 0.0)),
                base_confidence_score=float(s.get("base_confidence_score", 0.0)),
                dgic_envelope=dgic_input
            )
            unified_signals.append(sig)
        except Exception as e:
            raise CoreAdapterValidationError("INVALID_SIGNAL_FORMAT", f"Failed to parse signal {idx}: {str(e)}")
            
    try:
        agg_result = aggregate_unified_signals(unified_signals)
        dgic_envelope = wrap_in_dgic_envelope(agg_result)
        telemetry = emit_telemetry_event(execution_id, dgic_envelope)
        
        return CoreEnforcementPayload(
            aggregate_risk_score=dgic_envelope.aggregate_risk_score,
            aggregate_risk_category=dgic_envelope.aggregate_risk_category,
            aggregate_confidence=dgic_envelope.epistemic_confidence,
            signal_count=dgic_envelope.signal_count,
            active_signal_count=dgic_envelope.active_signal_count,
            epistemic_confidence=dgic_envelope.epistemic_confidence,
            signal_lineage=dgic_envelope.signal_lineage,
            collapse_state=dgic_envelope.collapse_state,
            truth_boundary_reference=dgic_envelope.truth_boundary_reference,
            telemetry_signal_id=telemetry.signal_id,
            telemetry_timestamp=telemetry.timestamp,
            safety_metadata=dgic_envelope.safety_metadata,
            errors=dgic_envelope.errors
        )
    except Exception as e:
        raise CoreAdapterValidationError("AGGREGATION_FAILED", f"Aggregation failed: {str(e)}")

def payload_to_dict(payload: CoreEnforcementPayload) -> Dict[str, Any]:
    from dataclasses import asdict
    return asdict(payload)
