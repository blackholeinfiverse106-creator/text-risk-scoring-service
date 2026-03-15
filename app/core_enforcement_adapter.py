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
  - All transformations are purely structural — no ML, no probabilistic inference.
  - Invalid signals are REJECTED, never silently dropped or mutated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

from app.dgic_adapter import (
    DGICInput,
    DGICPayload,
    EpistemicState,
    validate_dgic_input,
    compute_envelope_hash,
    DGICContractViolation,
)
from app.signal_aggregator import (
    UnifiedSignal,
    SignalType,
    aggregate_unified_signals,
    AggregatedUnifiedSignal,
)
from app.enforcement_aggregator import AggregationContractViolation
from app.dgic_enforcement_bridge import wrap_in_dgic_envelope, DGICEnforcementEnvelope
from app.insightbridge_telemetry import emit_telemetry_event, InsightBridgeTelemetryEvent

logger = logging.getLogger(__name__)


# ============================================================
# Frozen safety metadata
# ============================================================

_SAFETY_METADATA = {
    "is_decision": False,
    "authority": "NONE",
    "actionable": False,
}


# ============================================================
# Validation Error
# ============================================================

class CoreAdapterValidationError(Exception):
    """Raised when inbound signals fail Core schema validation."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


# ============================================================
# Output Dataclass
# ============================================================

@dataclass(frozen=True)
class CoreEnforcementPayload:
    """
    Core-compatible enforcement payload produced by the adapter.
    Consumable by the Core orchestration pipeline.
    """
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


# ============================================================
# Schema Validation
# ============================================================

VALID_SIGNAL_TYPES = {st.value for st in SignalType}

def validate_inbound_signal(raw: Dict[str, Any], index: int) -> UnifiedSignal:
    """
    Validate and parse a single inbound signal dict into a UnifiedSignal.
    Raises CoreAdapterValidationError on any structural failure.
    """
    # --- Required top-level fields ---
    required_fields = {"signal_id", "signal_type", "base_risk_score", "base_confidence_score", "dgic_envelope"}
    missing = required_fields - set(raw.keys())
    if missing:
        raise CoreAdapterValidationError(
            "MISSING_SIGNAL_FIELDS",
            f"signals[{index}] missing required fields: {sorted(missing)}"
        )

    # --- signal_id ---
    signal_id = raw["signal_id"]
    if not isinstance(signal_id, str) or not signal_id.strip():
        raise CoreAdapterValidationError(
            "INVALID_SIGNAL_ID",
            f"signals[{index}].signal_id must be a non-empty string"
        )

    # --- signal_type ---
    signal_type_raw = raw["signal_type"]
    if signal_type_raw not in VALID_SIGNAL_TYPES:
        raise CoreAdapterValidationError(
            "INVALID_SIGNAL_TYPE",
            f"signals[{index}].signal_type must be one of {sorted(VALID_SIGNAL_TYPES)}, got '{signal_type_raw}'"
        )
    signal_type = SignalType(signal_type_raw)

    # --- base_risk_score ---
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

    # --- base_confidence_score ---
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

    # --- dgic_envelope ---
    dgic_raw = raw["dgic_envelope"]
    if not isinstance(dgic_raw, dict):
        raise CoreAdapterValidationError(
            "INVALID_DGIC_ENVELOPE_TYPE",
            f"signals[{index}].dgic_envelope must be a dict"
        )

    # Parse DGIC envelope structurally
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

    # Parse epistemic state
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

    # Validate via DGIC contract
    try:
        validate_dgic_input(dgic)
    except DGICContractViolation as e:
        raise CoreAdapterValidationError(
            "DGIC_CONTRACT_VIOLATION",
            f"signals[{index}].dgic_envelope: {str(e)}"
        )

    return dgic


# ============================================================
# Core Pipeline
# ============================================================

def process_for_core(signals_raw: List[Dict[str, Any]]) -> CoreEnforcementPayload:
    """
    Full Core orchestration pipeline:
      1. Validate all inbound signals
      2. Aggregate via multi-signal aggregator
      3. Wrap in DGIC epistemic envelope
      4. Emit InsightBridge telemetry
      5. Return Core-compatible payload

    Raises CoreAdapterValidationError on invalid input.
    """
    if not isinstance(signals_raw, list) or len(signals_raw) == 0:
        raise CoreAdapterValidationError("EMPTY_SIGNALS", "At least one signal is required")

    logger.info(
        "Core adapter: validating inbound signals",
        extra={"event_type": "core_adapter_validate", "signal_count": len(signals_raw)},
    )

    # Step 1: Validate and parse
    unified_signals: List[UnifiedSignal] = []
    for i, raw in enumerate(signals_raw):
        sig = validate_inbound_signal(raw, i)
        unified_signals.append(sig)

    # Step 2: Aggregate
    agg = aggregate_unified_signals(unified_signals)

    # Step 3: DGIC envelope
    envelope = wrap_in_dgic_envelope(agg)

    # Step 4: Telemetry
    telemetry = emit_telemetry_event(envelope)

    # Step 5: Build Core payload
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
