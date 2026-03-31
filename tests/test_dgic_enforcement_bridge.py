import pytest
import hashlib
import json
from app.layer3_dgic import (
    wrap_in_dgic_envelope,
    CollapseState,
    _derive_collapse_state,
    _compute_signal_lineage,
)
from app.layer6_insightbridge import (
    UnifiedSignal,
    SignalType,
    aggregate_unified_signals,
)
from app.layer3_dgic import (
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


def _make_signal(sid: str, stype: SignalType, risk: float, conf: float, state: EpistemicState, contra: bool = False):
    return UnifiedSignal(
        signal_id=sid,
        signal_type=stype,
        base_risk_score=risk,
        base_confidence_score=conf,
        dgic_envelope=_make_dgic(state, contradiction=contra),
    )


# ── Collapse State Tests ──

def test_collapse_state_stable():
    sig = _make_signal("s1", SignalType.TEXT_RISK_SIGNAL, 0.5, 1.0, EpistemicState.KNOWN)
    agg = aggregate_unified_signals([sig])
    envelope = wrap_in_dgic_envelope(agg)
    assert envelope.collapse_state == CollapseState.STABLE


def test_collapse_state_degraded_warning():
    sig = _make_signal("s1", SignalType.TEXT_RISK_SIGNAL, 0.5, 1.0, EpistemicState.AMBIGUOUS)
    agg = aggregate_unified_signals([sig])
    envelope = wrap_in_dgic_envelope(agg)
    assert envelope.collapse_state == CollapseState.DEGRADED


def test_collapse_state_collapsed():
    sig = _make_signal("s1", SignalType.TEXT_RISK_SIGNAL, 0.5, 1.0, EpistemicState.UNKNOWN)
    agg = aggregate_unified_signals([sig])
    envelope = wrap_in_dgic_envelope(agg)
    assert envelope.collapse_state == CollapseState.COLLAPSED


# ── Envelope Field Tests ──

def test_envelope_fields_present():
    sig = _make_signal("s1", SignalType.POLICY_VIOLATION_SIGNAL, 0.8, 0.9, EpistemicState.KNOWN)
    agg = aggregate_unified_signals([sig])
    envelope = wrap_in_dgic_envelope(agg)

    assert isinstance(envelope.epistemic_confidence, float)
    assert isinstance(envelope.signal_lineage, str)
    assert len(envelope.signal_lineage) == 64  # SHA-256 hex
    assert isinstance(envelope.truth_boundary_reference, str)
    assert len(envelope.truth_boundary_reference) == 64
    assert 0.0 <= envelope.aggregate_risk_score <= 1.0
    assert envelope.aggregate_risk_category in ("LOW", "MEDIUM", "HIGH")


def test_envelope_safety_invariants():
    sig = _make_signal("s1", SignalType.TEXT_RISK_SIGNAL, 0.9, 1.0, EpistemicState.KNOWN)
    agg = aggregate_unified_signals([sig])
    envelope = wrap_in_dgic_envelope(agg)

    assert envelope.safety_metadata["is_decision"] is False
    assert envelope.safety_metadata["authority"] == "NONE"
    assert envelope.safety_metadata["actionable"] is False


def test_lineage_deterministic():
    sig = _make_signal("s1", SignalType.TEXT_RISK_SIGNAL, 0.5, 1.0, EpistemicState.KNOWN)
    agg = aggregate_unified_signals([sig])
    e1 = wrap_in_dgic_envelope(agg)
    e2 = wrap_in_dgic_envelope(agg)
    assert e1.signal_lineage == e2.signal_lineage
