from __future__ import annotations
"""
Sovereign Layer File: app/layer4_core.py

Core Execution Layer — Pure Enforcement Pass-Through

This module does NOT interpret Sarathi's decision.
It receives the authoritative governance decision and:
  IF decision == ALLOW → pass to Core (executed = True)
  ELSE → block (executed = False)

NO interpretation allowed. No ESCALATE, no REQUEST_MORE_DATA mapping.
The raw Sarathi decision is preserved as-is.

Authority Boundary (IMMUTABLE):
  - This module NEVER evaluates risk, thresholds, or epistemic states.
  - All decision authority belongs to Sarathi (Layer 1).
  - This module ONLY executes Sarathi-approved decisions.
"""


import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict

from app.enforcement_schemas import (
    EvaluateActionRequest,
    SarathiEvaluateResponse,
    SarathiDecision,
    EnforcementDecision,
    ExecuteActionRequest,
    ExecuteActionResponse,
    ContextSignal,
    DGICEpistemicStateInput,
    SourceSystem,
)
from app.layer1_sarathi import evaluate_action as sarathi_evaluate
from app.layer5_bucket import record_decision, write_execution_record

logger = logging.getLogger(__name__)


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
        ..., description="ALLOW or BLOCK — the enforcement outcome"
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
        None, description="Null on ALLOW. Structured reason on BLOCK."
    )
    trace_hash: str = Field(
        ..., min_length=64, max_length=64,
        description="SHA-256 trace hash for deterministic replay"
    )
    gate_decision: EnforcementDecision = Field(
        ..., description="The raw Sarathi governance decision"
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
      3. Enforcement gate records the decision
      4. Pure pass-through: ALLOW → execute, anything else → BLOCK
      5. Log and return CoreExecutionResult

    NO interpretation. The Sarathi decision is the final word.
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

    # Step 2.5: EXECUTION ID GUARD (Phase 6)
    # Verify Sarathi returned the same execution_id we sent
    if sarathi_response.execution_id != execution_id:
        logger.error(
            f"EXECUTION ID MISMATCH: sent={execution_id}, received={sarathi_response.execution_id}",
            extra={
                "event_type": "execution_id_mismatch",
                "execution_id": execution_id,
                "sarathi_execution_id": sarathi_response.execution_id,
            },
        )
        return CoreExecutionResult(
            execution_id=execution_id,
            execution_decision=EnforcementDecision.BLOCK,
            executed=False,
            risk_score=0.0,
            confidence=0.0,
            failure_reason=f"Execution ID mismatch: pipeline sent '{execution_id}' but Sarathi returned '{sarathi_response.execution_id}'. Execution rejected.",
            trace_hash=sarathi_response.trace_hash,
            gate_decision=EnforcementDecision.BLOCK,
        )

    # Step 3: Enforcement gate records the decision (Layer 4 — execution)
    enforce_decision(request, sarathi_response)

    # Step 4: Pure pass-through — NO interpretation
    # ALLOW → execute. Everything else → BLOCK.
    sarathi_decision = sarathi_response.sarathi_decision

    if sarathi_decision == SarathiDecision.ALLOW:
        core_decision = EnforcementDecision.ALLOW
        executed = True
    else:
        core_decision = EnforcementDecision.BLOCK
        executed = False

    # Map raw Sarathi decision for the gate_decision field
    raw_gate = EnforcementDecision(sarathi_decision.value)

    # Step 5: Build result
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
            "sarathi_decision": sarathi_decision.value,
            "core_decision": core_decision.value,
            "executed": executed,
            "risk_score": sarathi_response.risk_score,
            "trace_hash": sarathi_response.trace_hash,
        },
    )

    return result


# ============================================================
# Enforcement Gate — Pure Execution
# ============================================================

def enforce_decision(
    request: EvaluateActionRequest,
    sarathi_response: SarathiEvaluateResponse,
    dgic_snapshot_dict: Optional[dict] = None,
) -> ExecuteActionResponse:
    """
    Enforce a Sarathi-approved decision.

    Pipeline:
      1. Map Sarathi decision to enforcement disposition (ALLOW → ALLOW, else → BLOCK)
      2. Record to enforcement ledger
      3. Write to persistent bucket
      4. Return ExecuteActionResponse

    This function NEVER evaluates risk. It only enforces.
    """
    execution_id = request.execution_id
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    # EXECUTION ID GUARD (Phase 6)
    if sarathi_response.execution_id != execution_id:
        logger.error(
            f"enforce_decision: execution_id mismatch | request={execution_id} sarathi={sarathi_response.execution_id}",
            extra={
                "event_type": "enforcement_execution_id_mismatch",
                "execution_id": execution_id,
                "sarathi_execution_id": sarathi_response.execution_id,
            },
        )
        return ExecuteActionResponse(
            execution_id=execution_id,
            enforcement_decision=EnforcementDecision.BLOCK,
            executed=False,
            trace_hash=sarathi_response.trace_hash,
        )

    logger.info(
        "Enforcement gate: enforcing Sarathi decision",
        extra={
            "execution_id": execution_id,
            "event_type": "enforcement_enforce_start",
            "sarathi_decision": sarathi_response.sarathi_decision.value,
            "source_system": request.source_system.value,
        },
    )

    # Step 1: Pure mapping — ALLOW → ALLOW, else → BLOCK
    if sarathi_response.sarathi_decision == SarathiDecision.ALLOW:
        enforcement_decision = EnforcementDecision.ALLOW
    else:
        enforcement_decision = EnforcementDecision(sarathi_response.sarathi_decision.value)

    executed = enforcement_decision == EnforcementDecision.ALLOW

    # Step 2: Record to enforcement ledger
    record_decision(
        execution_id=execution_id,
        timestamp_utc=timestamp_utc,
        request=request,
        sarathi_response=sarathi_response,
    )

    # Step 3: Build response
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


# ============================================================
# Core Enforcement Adapter (Unified Signal Pipeline)
# ============================================================

"""
Core Enforcement Adapter
=========================
Gateway module that validates inbound unified signals for Core orchestration
compatibility, runs the aggregation pipeline, and produces a Core-compatible
enforcement payload.

Authority Boundary (IMMUTABLE):
  - This module NEVER derives enforcement authority.
  - safety_metadata.is_decision remains False in all outputs.
  - safety_metadata.authority remains "NONE" in all outputs.
"""

from app.layer3_dgic import (
    DGICInput,
    DGICPayload,
    EpistemicState,
    validate_dgic_input,
    compute_envelope_hash,
    DGICContractViolation,
)
from app.layer6_insightbridge import (
    UnifiedSignal,
    SignalType,
    aggregate_unified_signals,
    AggregatedUnifiedSignal,
)
from app.layer6_insightbridge import AggregationContractViolation
from app.layer3_dgic import wrap_in_dgic_envelope, DGICEnforcementEnvelope
from app.layer6_insightbridge import emit_telemetry_event, InsightBridgeTelemetryEvent


_SAFETY_METADATA = {
    "is_decision": False,
    "authority": "NONE",
    "actionable": False,
}


class CoreAdapterValidationError(Exception):
    """Raised when inbound signals fail Core schema validation."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class CoreEnforcementPayload:
    """Core-compatible enforcement payload produced by the adapter."""
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


VALID_SIGNAL_TYPES = {st.value for st in SignalType}


def validate_inbound_signal(raw: Dict[str, Any], index: int) -> UnifiedSignal:
    """Validate and parse a single inbound signal dict into a UnifiedSignal."""
    required_fields = {"signal_id", "signal_type", "base_risk_score", "base_confidence_score", "dgic_envelope"}
    missing = required_fields - set(raw.keys())
    if missing:
        raise CoreAdapterValidationError(
            "MISSING_SIGNAL_FIELDS",
            f"signals[{index}] missing required fields: {sorted(missing)}"
        )

    signal_id = raw["signal_id"]
    if not isinstance(signal_id, str) or not signal_id.strip():
        raise CoreAdapterValidationError(
            "INVALID_SIGNAL_ID",
            f"signals[{index}].signal_id must be a non-empty string"
        )

    signal_type_raw = raw["signal_type"]
    if signal_type_raw not in VALID_SIGNAL_TYPES:
        raise CoreAdapterValidationError(
            "INVALID_SIGNAL_TYPE",
            f"signals[{index}].signal_type must be one of {sorted(VALID_SIGNAL_TYPES)}, got '{signal_type_raw}'"
        )
    signal_type = SignalType(signal_type_raw)

    risk = raw["base_risk_score"]
    if not isinstance(risk, (int, float)) or isinstance(risk, bool):
        raise CoreAdapterValidationError(
            "INVALID_RISK_SCORE_TYPE",
            f"signals[{index}].base_risk_score must be a number"
        )
    if not (0.0 <= float(risk) <= 1.0):
        raise CoreAdapterValidationError(
            "INVALID_RISK_SCORE_RANGE",
            f"signals[{index}].base_risk_score must be in [0.0, 1.0], got {risk}"
        )

    conf = raw["base_confidence_score"]
    if not isinstance(conf, (int, float)) or isinstance(conf, bool):
        raise CoreAdapterValidationError(
            "INVALID_CONFIDENCE_SCORE_TYPE",
            f"signals[{index}].base_confidence_score must be a number"
        )
    if not (0.0 <= float(conf) <= 1.0):
        raise CoreAdapterValidationError(
            "INVALID_CONFIDENCE_SCORE_RANGE",
            f"signals[{index}].base_confidence_score must be in [0.0, 1.0], got {conf}"
        )

    dgic_raw = raw["dgic_envelope"]
    if not isinstance(dgic_raw, dict):
        raise CoreAdapterValidationError(
            "INVALID_DGIC_ENVELOPE_TYPE",
            f"signals[{index}].dgic_envelope must be a dict"
        )

    try:
        dgic = _parse_dgic_envelope(dgic_raw, index)
    except CoreAdapterValidationError:
        raise
    except Exception as e:
        raise CoreAdapterValidationError(
            "INVALID_DGIC_ENVELOPE",
            f"signals[{index}].dgic_envelope parsing failed: {str(e)}"
        )

    return UnifiedSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        base_risk_score=float(risk),
        base_confidence_score=float(conf),
        dgic_envelope=dgic,
    )


def _parse_dgic_envelope(raw: Dict[str, Any], index: int) -> DGICInput:
    """Parse and validate a raw DGIC envelope dict into a DGICInput."""
    required = {"version", "lineage_hash", "envelope_hash", "payload"}
    missing = required - set(raw.keys())
    if missing:
        raise CoreAdapterValidationError(
            "MISSING_DGIC_FIELDS",
            f"signals[{index}].dgic_envelope missing: {sorted(missing)}"
        )

    payload_raw = raw["payload"]
    if not isinstance(payload_raw, dict):
        raise CoreAdapterValidationError(
            "INVALID_DGIC_PAYLOAD",
            f"signals[{index}].dgic_envelope.payload must be a dict"
        )

    state_raw = payload_raw.get("epistemic_state")
    try:
        state = EpistemicState(state_raw)
    except (ValueError, KeyError):
        raise CoreAdapterValidationError(
            "INVALID_EPISTEMIC_STATE",
            f"signals[{index}].dgic_envelope.payload.epistemic_state invalid: '{state_raw}'"
        )

    entropy = payload_raw.get("entropy_score", 0.0)
    contradiction = payload_raw.get("contradiction_flag", False)
    collapse = raw.get("collapse_flag", False)

    payload = DGICPayload(
        epistemic_state=state,
        entropy_score=float(entropy),
        contradiction_flag=bool(contradiction),
    )

    dgic = DGICInput(
        version=raw["version"],
        lineage_hash=raw["lineage_hash"],
        envelope_hash=raw["envelope_hash"],
        payload=payload,
        collapse_flag=bool(collapse),
    )

    try:
        validate_dgic_input(dgic)
    except DGICContractViolation as e:
        raise CoreAdapterValidationError(
            "DGIC_CONTRACT_VIOLATION",
            f"signals[{index}].dgic_envelope: {str(e)}"
        )

    return dgic


def process_for_core(signals_raw: List[Dict[str, Any]]) -> CoreEnforcementPayload:
    """
    Full Core orchestration pipeline:
      1. Validate all inbound signals
      2. Aggregate via multi-signal aggregator
      3. Wrap in DGIC epistemic envelope
      4. Emit InsightBridge telemetry
      5. Return Core-compatible payload
    """
    if not isinstance(signals_raw, list) or len(signals_raw) == 0:
        raise CoreAdapterValidationError("EMPTY_SIGNALS", "At least one signal is required")

    logger.info(
        "Core adapter: validating inbound signals",
        extra={"event_type": "core_adapter_validate", "signal_count": len(signals_raw)},
    )

    unified_signals: List[UnifiedSignal] = []
    for i, raw in enumerate(signals_raw):
        sig = validate_inbound_signal(raw, i)
        unified_signals.append(sig)

    agg = aggregate_unified_signals(unified_signals)
    envelope = wrap_in_dgic_envelope(agg)
    telemetry = emit_telemetry_event(envelope)

    payload = CoreEnforcementPayload(
        aggregate_risk_score=agg.aggregate_risk_score,
        aggregate_risk_category=agg.aggregate_risk_category,
        aggregate_confidence=agg.aggregate_confidence,
        signal_count=agg.signal_count,
        active_signal_count=agg.active_signal_count,
        epistemic_confidence=envelope.epistemic_confidence,
        signal_lineage=envelope.signal_lineage,
        collapse_state=envelope.collapse_state,
        truth_boundary_reference=envelope.truth_boundary_reference,
        telemetry_signal_id=telemetry.signal_id,
        telemetry_timestamp=telemetry.timestamp,
        safety_metadata=dict(_SAFETY_METADATA),
        errors=agg.errors,
    )

    logger.info(
        "Core adapter: payload ready",
        extra={
            "event_type": "core_adapter_complete",
            "aggregate_risk_score": payload.aggregate_risk_score,
            "collapse_state": payload.collapse_state,
        },
    )

    return payload


def payload_to_dict(payload: CoreEnforcementPayload) -> Dict[str, Any]:
    """Serialize CoreEnforcementPayload to a plain dict for JSON responses."""
    return asdict(payload)
