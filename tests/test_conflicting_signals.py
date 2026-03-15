"""
Conflicting Signal Tests
=========================
Tests covering: full contradiction density, mixed contradiction/clean,
contradiction penalty math, contradictions don't inflate scores.
"""
import pytest
from app.signal_aggregator import (
    UnifiedSignal, SignalType, aggregate_unified_signals,
)
from app.dgic_adapter import (
    DGICInput, DGICPayload, EpistemicState, compute_envelope_hash,
)

LINEAGE = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

def _dgic(state=EpistemicState.KNOWN, entropy=0.0, contra=False):
    payload = DGICPayload(epistemic_state=state, entropy_score=entropy, contradiction_flag=contra)
    pd = {"epistemic_state": state.value, "entropy_score": entropy, "contradiction_flag": contra}
    eh = compute_envelope_hash("schema_v1", LINEAGE, pd)
    return DGICInput(version="schema_v1", lineage_hash=LINEAGE, envelope_hash=eh, payload=payload)

def _sig(sid, stype, risk, conf, contra=False, state=EpistemicState.KNOWN):
    return UnifiedSignal(signal_id=sid, signal_type=stype,
                         base_risk_score=risk, base_confidence_score=conf,
                         dgic_envelope=_dgic(state, contra=contra))


# ── Full contradiction density ──

def test_all_signals_contradicting():
    """D=1.0 → penalty factor = 1.0 - 1.0*0.5 = 0.5 → score halved."""
    sigs = [
        _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.8, 1.0, contra=True),
        _sig("s2", SignalType.BEHAVIOR_ANOMALY_SIGNAL, 0.8, 1.0, contra=True),
    ]
    r = aggregate_unified_signals(sigs)
    assert r.contradiction_density == 1.0
    assert r.contradiction_penalty_applied == pytest.approx(0.5, abs=0.01)
    # 0.8 * 0.5 = 0.4
    assert r.aggregate_risk_score == pytest.approx(0.4, abs=0.02)


def test_half_signals_contradicting():
    """D=0.5 → penalty factor = 0.75 → score * 0.75."""
    sigs = [
        _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.8, 1.0, contra=True),
        _sig("s2", SignalType.TEXT_RISK_SIGNAL, 0.8, 1.0, contra=True),
        _sig("s3", SignalType.TEXT_RISK_SIGNAL, 0.8, 1.0, contra=False),
        _sig("s4", SignalType.TEXT_RISK_SIGNAL, 0.8, 1.0, contra=False),
    ]
    r = aggregate_unified_signals(sigs)
    assert r.contradiction_density == pytest.approx(0.5, abs=0.01)
    assert r.contradiction_penalty_applied == pytest.approx(0.75, abs=0.01)
    assert r.aggregate_risk_score == pytest.approx(0.6, abs=0.02)


def test_no_contradictions():
    """D=0.0 → penalty factor = 1.0 → no penalty."""
    sigs = [
        _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.6, 1.0, contra=False),
        _sig("s2", SignalType.BEHAVIOR_ANOMALY_SIGNAL, 0.6, 1.0, contra=False),
    ]
    r = aggregate_unified_signals(sigs)
    assert r.contradiction_density == 0.0
    assert r.contradiction_penalty_applied == 1.0


# ── Contradiction must not inflate score ──

def test_contradiction_never_inflates():
    """Adding contradicting signals should never make the aggregate higher than without."""
    base = [_sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.7, 1.0, contra=False)]
    r_base = aggregate_unified_signals(base)

    with_contra = [
        _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.7, 1.0, contra=False),
        _sig("s2", SignalType.TEXT_RISK_SIGNAL, 0.7, 1.0, contra=True),
    ]
    r_contra = aggregate_unified_signals(with_contra)

    # With contradiction, score should be <= base score
    assert r_contra.aggregate_risk_score <= r_base.aggregate_risk_score + 0.01


# ── Mixed contradiction + ambiguous ──

def test_contradicting_plus_ambiguous():
    """Contradictions + AMBIGUOUS epistemic state should not escalate to HIGH."""
    sigs = [
        _sig("s1", SignalType.POLICY_VIOLATION_SIGNAL, 0.95, 1.0, contra=True, state=EpistemicState.AMBIGUOUS),
        _sig("s2", SignalType.TEXT_RISK_SIGNAL, 0.95, 1.0, contra=True, state=EpistemicState.AMBIGUOUS),
    ]
    r = aggregate_unified_signals(sigs)
    # AMBIGUOUS caps at 0.69, then contradiction penalty halves it further
    assert r.aggregate_risk_score <= 0.69


# ── Contradiction + abstain mix ──

def test_contradicting_plus_abstaining():
    """One contradicting active + one abstaining → aggregate is from active only, penalized."""
    sigs = [
        _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.8, 1.0, contra=True),
        _sig("s2", SignalType.BEHAVIOR_ANOMALY_SIGNAL, 0.5, 1.0, contra=False, state=EpistemicState.UNKNOWN),
    ]
    r = aggregate_unified_signals(sigs)
    assert r.active_signal_count == 1
    assert r.abstained_signal_count == 1
    # D = 1/2 = 0.5 → penalty = 0.75
    assert r.contradiction_density == 0.5
    assert r.aggregate_risk_score > 0.0  # active signal contributes


# ── Safety always holds under conflict ──

def test_safety_under_max_conflict():
    sigs = [
        _sig(f"s{i}", SignalType.TEXT_RISK_SIGNAL, 1.0, 1.0, contra=True)
        for i in range(10)
    ]
    r = aggregate_unified_signals(sigs)
    assert r.safety_metadata["is_decision"] is False
    assert r.safety_metadata["authority"] == "NONE"
    assert r.safety_metadata["actionable"] is False
