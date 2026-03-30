import pytest
from app.insightbridge_telemetry import (
    emit_telemetry_event,
    emit_telemetry_dict,
    InsightBridgeTelemetryEvent,
)
from app.dgic_enforcement_bridge import wrap_in_dgic_envelope
from app.signal_aggregator import (
    UnifiedSignal,
    SignalType,
    aggregate_unified_signals,
)
from app.dgic_adapter import (
    DGICInput,
    DGICPayload,
    EpistemicState,
    compute_envelope_hash,
)


def _make_dgic(state: EpistemicState, contradiction: bool = False, entropy: float = 0.0) -> DGICInput:
    payload = DGICPayload(epistemic_state=state, entropy_score=entropy, contradiction_flag=contradiction)
    payload_dict = {
        "epistemic_state": payload.epistemic_state.value,
        "entropy_score": payload.entropy_score,
        "contradiction_flag": payload.contradiction_flag,
    }
    lineage = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    envelope_hash = compute_envelope_hash("schema_v1", lineage, payload_dict)
    return DGICInput(version="schema_v1", lineage_hash=lineage, envelope_hash=envelope_hash, payload=payload)


def _make_signal(sid: str, stype: SignalType, risk: float, conf: float, state: EpistemicState):
    return UnifiedSignal(
        signal_id=sid,
        signal_type=stype,
        base_risk_score=risk,
        base_confidence_score=conf,
        dgic_envelope=_make_dgic(state),
    )


def test_telemetry_event_fields():
    sig = _make_signal("s1", SignalType.TEXT_RISK_SIGNAL, 0.6, 0.9, EpistemicState.KNOWN)
    agg = aggregate_unified_signals([sig])
    envelope = wrap_in_dgic_envelope(agg)
    event = emit_telemetry_event("exec-1", envelope)

    assert isinstance(event, InsightBridgeTelemetryEvent)
    assert event.signal_source == "multi_signal_aggregator"
    assert isinstance(event.signal_id, str) and len(event.signal_id) == 64
    assert isinstance(event.timestamp, str)
    assert isinstance(event.confidence, float)
    assert isinstance(event.lineage_reference, str) and len(event.lineage_reference) == 64
    assert isinstance(event.risk_score, float)
    assert isinstance(event.signal_count, int)
    assert event.collapse_state in ("STABLE", "DEGRADED", "COLLAPSED")


def test_telemetry_dict_format():
    sig = _make_signal("s1", SignalType.POLICY_VIOLATION_SIGNAL, 0.8, 1.0, EpistemicState.KNOWN)
    agg = aggregate_unified_signals([sig])
    envelope = wrap_in_dgic_envelope(agg)
    result = emit_telemetry_dict("exec-1", envelope)

    assert isinstance(result, dict)
    required_keys = {"signal_id", "signal_source", "confidence", "timestamp", "lineage_reference", "risk_score", "signal_count", "collapse_state"}
    assert required_keys.issubset(set(result.keys()))


def test_telemetry_collapsed_state():
    sig = _make_signal("s1", SignalType.TEXT_RISK_SIGNAL, 0.8, 1.0, EpistemicState.UNKNOWN)
    agg = aggregate_unified_signals([sig])
    envelope = wrap_in_dgic_envelope(agg)
    event = emit_telemetry_event("exec-2", envelope)

    assert event.collapse_state == "COLLAPSED"
    assert event.risk_score == 0.0


def test_telemetry_deterministic_signal_id():
    sig = _make_signal("s1", SignalType.TEXT_RISK_SIGNAL, 0.5, 1.0, EpistemicState.KNOWN)
    agg = aggregate_unified_signals([sig])
    envelope = wrap_in_dgic_envelope(agg)
    e1 = emit_telemetry_event("exec-3", envelope)
    e2 = emit_telemetry_event("exec-3", envelope)
    assert e1.signal_id == e2.signal_id  # Same envelope → same signal_id
