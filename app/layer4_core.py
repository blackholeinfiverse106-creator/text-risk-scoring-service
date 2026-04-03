from __future__ import annotations
"""
Sovereign Layer File: app/layer4_core.py

Core Execution Layer — Raj Prajapati's Domain
==============================================

This module is the Core execution pipeline. It:
  1. Calls Sarathi for governance decision
  2. Passes Sarathi decision + DGIC snapshot to the Enforcement Gate
  3. Based on enforcement verdict, Core maps execution outcomes
  4. Core writes to Bucket (not enforcement)
  5. Returns CoreExecutionResult

Authority Boundary (IMMUTABLE):
  - Sarathi (Layer 1) owns governance decisions.
  - Enforcement Gate (layer4_enforcement) validates sovereign compliance.
  - Core owns execution mapping (executed flag) and Bucket recording.
  - This module NEVER evaluates risk, thresholds, or epistemic states.
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
    ContextSignal,
    DGICEpistemicStateInput,
    SourceSystem,
)
from app.layer1_sarathi import evaluate_action as sarathi_evaluate
from app.layer5_bucket import write_execution_record
from app.layer4_enforcement import enforce, EnforcementVerdict, EnforcementHardFailure
from app.layer6_insightbridge import emit_enforcement_telemetry

logger = logging.getLogger(__name__)


# ============================================================
# Core Execution Result
# ============================================================

class CoreExecutionResult(BaseModel):
    """
    Phase 8 Clean Decision Contract.
    The final output of submitting an action proposal to the Core pipeline.
    Execution flags are STRICTLY PROHIBITED.
    """
    execution_id: str = Field(
        ..., description="The original execution ID"
    )
    enforcement_decision: EnforcementDecision = Field(
        ..., description="ALLOW | DENY | ABSTAIN — final deterministic gate output"
    )
    risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Final computed risk score from Sarathi"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Decision confidence from Sarathi"
    )
    trace_hash: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 trace hash for deterministic replay"
    )
    failure_reason: Optional[str] = Field(
        None, description="Null on ALLOW. Structured reason on DENY/ABSTAIN."
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
    Submit an action proposal to the Core execution pipeline.

    Pipeline:
      1. Build EvaluateActionRequest from proposal fields
      2. Sarathi evaluates the proposal (governance decision)
      3. EXECUTION ID GUARD — verify Sarathi returned same execution_id
      4. Enforcement gate validates sovereign compliance (HARD FAIL if invalid)
      5. Core maps enforcement verdict to execution outcome (Core owns this)
      6. Core records to Bucket (Core owns this, not enforcement)
      7. Return CoreExecutionResult

    Sovereign Law: Sarathi decides. Enforcement validates. Core executes.
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

    # Step 2: Sarathi governance evaluation (Layer 1 — Aakanksha's decision authority)
    sarathi_response: SarathiEvaluateResponse = sarathi_evaluate(request)

    # Step 3: EXECUTION ID GUARD (Phase 6)
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
        result = CoreExecutionResult(
            execution_id=execution_id,
            enforcement_decision=EnforcementDecision.DENY,
            risk_score=0.0,
            confidence=0.0,
            trace_hash=sarathi_response.trace_hash,
            failure_reason=f"Execution ID mismatch: pipeline sent '{execution_id}' but Sarathi returned '{sarathi_response.execution_id}'. Execution rejected."
        )
        emit_enforcement_telemetry(
            execution_id=result.execution_id,
            enforcement_decision=result.enforcement_decision.value,
            risk_score=result.risk_score,
            confidence=result.confidence,
            trace_hash=result.trace_hash,
        )
        return result

    # Step 4: Enforcement gate — sovereign compliance validation
    # Build DGIC snapshot for enforcement (read-only context)
    dgic_snapshot_dict = dgic_epistemic_state.model_dump(mode="json")

    try:
        verdict: EnforcementVerdict = enforce(
            original_execution_id=execution_id,
            sarathi_decision=sarathi_response.sarathi_decision.value,
            sarathi_execution_id=sarathi_response.execution_id,
            sarathi_trace_hash=sarathi_response.trace_hash,
            sarathi_failure_reason=sarathi_response.failure_reason,
            dgic_snapshot=dgic_snapshot_dict,
        )
    except EnforcementHardFailure as e:
        logger.error(
            f"Enforcement hard failure | execution_id={execution_id} | {e.code}: {e.message}",
            extra={
                "event_type": "enforcement_hard_failure",
                "execution_id": execution_id,
                "code": e.code,
            },
        )
        result = CoreExecutionResult(
            execution_id=execution_id,
            enforcement_decision=EnforcementDecision.DENY,
            risk_score=0.0,
            confidence=0.0,
            trace_hash=sarathi_response.trace_hash,
            failure_reason=f"Enforcement hard failure: {e.code} — {e.message}"
        )
        emit_enforcement_telemetry(
            execution_id=result.execution_id,
            enforcement_decision=result.enforcement_decision.value,
            risk_score=result.risk_score,
            confidence=result.confidence,
            trace_hash=result.trace_hash,
        )
        return result

    # Step 5: Route Enforcement Core Decision (Execution map decoupled to clients)
    if verdict.verdict == "ALLOW":
        core_decision = EnforcementDecision.ALLOW
    elif verdict.verdict == "ABSTAIN":
        core_decision = EnforcementDecision.ABSTAIN
    else:
        core_decision = EnforcementDecision.DENY

    # Step 6: Core records to Bucket
    write_execution_record(
        execution_id=execution_id,
        decision=core_decision.value,
        risk_score=sarathi_response.risk_score,
        confidence=sarathi_response.confidence,
        trace_hash=sarathi_response.trace_hash,
        request_payload=request.model_dump(mode="json"),
        dgic_snapshot=dgic_snapshot_dict,
        failure_reason=verdict.reasoning,
    )

    # Step 7: Build Phase 8 result
    result = CoreExecutionResult(
        execution_id=execution_id,
        enforcement_decision=core_decision,
        risk_score=sarathi_response.risk_score,
        confidence=sarathi_response.confidence,
        trace_hash=sarathi_response.trace_hash,
        failure_reason=verdict.reasoning,
    )

    logger.info(
        f"Core execution result: {core_decision.value}",
        extra={
            "event_type": "core_execution_result",
            "execution_id": execution_id,
            "enforcement_verdict": verdict.verdict,
            "enforcement_decision": core_decision.value,
            "risk_score": sarathi_response.risk_score,
            "trace_hash": sarathi_response.trace_hash,
        },
    )

    emit_enforcement_telemetry(
        execution_id=result.execution_id,
        enforcement_decision=result.enforcement_decision.value,
        risk_score=result.risk_score,
        confidence=result.confidence,
        trace_hash=result.trace_hash,
    )

    return result


# ============================================================
# NOTE: enforce_decision() REMOVED — Sovereign Law Compliance
# ============================================================
# The old enforce_decision() function violated Sovereign Core Law:
#   - It owned execution mapping (executed flag)
#   - It wrote to Bucket directly (record_decision)
#   - It re-interpreted Sarathi decisions
#
# Enforcement is now in layer4_enforcement.py (pure gate).
# Core (this module) owns execution + bucket recording.
# ============================================================


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
