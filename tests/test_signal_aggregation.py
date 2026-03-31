"""
Multi-Signal Aggregation Scenarios
===================================
Tests covering: mixed signal types, varying weights, partial abstention,
all-abstain edge case, single-signal, and full 4-type aggregation.
"""
import pytest
from app.layer6_insightbridge import (
    UnifiedSignal, SignalType, aggregate_unified_signals,
)
from app.layer3_dgic import (
    DGICInput, DGICPayload, EpistemicState, compute_envelope_hash,
)

LINEAGE = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

def _dgic(state=EpistemicState.KNOWN, entropy=0.0, contra=False):
    payload = DGICPayload(epistemic_state=state, entropy_score=entropy, contradiction_flag=contra)
    pd = {"epistemic_state": state.value, "entropy_score": entropy, "contradiction_flag": contra}
    eh = compute_envelope_hash("schema_v1", LINEAGE, pd)
    return DGICInput(version="schema_v1", lineage_hash=LINEAGE, envelope_hash=eh, payload=payload)

def _sig(sid, stype, risk, conf, state=EpistemicState.KNOWN, entropy=0.0, contra=False):
    return UnifiedSignal(signal_id=sid, signal_type=stype,
                         base_risk_score=risk, base_confidence_score=conf,
                         dgic_envelope=_dgic(state, entropy, contra))


# ── Single signal ──

def test_single_text_risk_signal():
    r = aggregate_unified_signals([_sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.5, 1.0)])
    assert r.signal_count == 1
    assert r.active_signal_count == 1
    assert 0.0 <= r.aggregate_risk_score <= 1.0
    assert r.safety_metadata["authority"] == "NONE"

def test_single_policy_violation_signal():
    r = aggregate_unified_signals([_sig("s1", SignalType.POLICY_VIOLATION_SIGNAL, 0.9, 1.0)])
    assert r.aggregate_risk_score > 0.0
    assert r.aggregate_risk_category in ("LOW", "MEDIUM", "HIGH")


# ── Mixed signal types ──

def test_mixed_two_signals():
    sigs = [
        _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.4, 1.0),
        _sig("s2", SignalType.BEHAVIOR_ANOMALY_SIGNAL, 0.6, 0.8),
    ]
    r = aggregate_unified_signals(sigs)
    assert r.signal_count == 2
    assert r.active_signal_count == 2
    assert r.abstained_signal_count == 0

def test_full_four_signal_types():
    sigs = [
        _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.3, 0.9),
        _sig("s2", SignalType.BEHAVIOR_ANOMALY_SIGNAL, 0.5, 0.8),
        _sig("s3", SignalType.POLICY_VIOLATION_SIGNAL, 0.7, 1.0),
        _sig("s4", SignalType.EXTERNAL_DETECTOR_SIGNAL, 0.2, 0.7),
    ]
    r = aggregate_unified_signals(sigs)
    assert r.signal_count == 4
    assert r.active_signal_count == 4
    # Policy violation has highest weight (1.5), so aggregate should skew towards it
    assert r.aggregate_risk_score > 0.2


# ── Partial abstention ──

def test_partial_abstention():
    sigs = [
        _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.8, 1.0, EpistemicState.KNOWN),
        _sig("s2", SignalType.BEHAVIOR_ANOMALY_SIGNAL, 0.5, 1.0, EpistemicState.UNKNOWN),
    ]
    r = aggregate_unified_signals(sigs)
    assert r.signal_count == 2
    assert r.active_signal_count == 1
    assert r.abstained_signal_count == 1
    assert r.any_abstained is True
    assert r.all_abstained is False
    assert r.aggregate_risk_score > 0.0  # active signal still contributes


# ── All abstain ──

def test_all_abstain():
    sigs = [
        _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.9, 1.0, EpistemicState.UNKNOWN),
        _sig("s2", SignalType.POLICY_VIOLATION_SIGNAL, 0.9, 1.0, EpistemicState.UNKNOWN),
    ]
    r = aggregate_unified_signals(sigs)
    assert r.all_abstained is True
    assert r.aggregate_risk_score == 0.0
    assert r.aggregate_risk_category == "LOW"
    assert r.errors is not None
    assert r.errors["error_code"] == "ALL_SIGNALS_ABSTAINED"


# ── Inferred state with entropy ──

def test_inferred_entropy_scaling():
    # High entropy should reduce confidence
    sigs = [
        _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.8, 1.0, EpistemicState.INFERRED, entropy=0.9),
    ]
    r = aggregate_unified_signals(sigs)
    assert r.aggregate_confidence < 1.0  # Scaled down by entropy


# ── Score is bounded ──

def test_score_bounded():
    sigs = [
        _sig("s1", SignalType.POLICY_VIOLATION_SIGNAL, 1.0, 1.0),
        _sig("s2", SignalType.BEHAVIOR_ANOMALY_SIGNAL, 1.0, 1.0),
        _sig("s3", SignalType.TEXT_RISK_SIGNAL, 1.0, 1.0),
    ]
    r = aggregate_unified_signals(sigs)
    assert r.aggregate_risk_score <= 1.0


# ── Safety invariants always hold ──

def test_safety_invariants_always_hold():
    sigs = [
        _sig("s1", SignalType.POLICY_VIOLATION_SIGNAL, 1.0, 1.0),
        _sig("s2", SignalType.TEXT_RISK_SIGNAL, 0.0, 0.0, EpistemicState.UNKNOWN),
    ]
    r = aggregate_unified_signals(sigs)
    assert r.safety_metadata["is_decision"] is False
    assert r.safety_metadata["authority"] == "NONE"
    assert r.safety_metadata["actionable"] is False
