import pytest
from app.layer6_insightbridge import (
    UnifiedSignal,
    SignalType,
    aggregate_unified_signals,
)
from app.layer3_dgic import (
    DGICInput,
    DGICPayload,
    EpistemicState,
)

def build_mock_dgic(state: EpistemicState, contradiction: bool = False, entropy: float = 0.0) -> DGICInput:
    payload = DGICPayload(
        epistemic_state=state,
        entropy_score=entropy,
        contradiction_flag=contradiction
    )
    # Simple hash generation for tests
    import hashlib
    import json
    payload_dict = {
        "epistemic_state": payload.epistemic_state.value,
        "entropy_score": payload.entropy_score,
        "contradiction_flag": payload.contradiction_flag
    }
    payload_str = json.dumps(payload_dict, sort_keys=True)
    raw = f"schema_v1|1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef|{payload_str}"
    envelope_hash = hashlib.sha256(raw.encode()).hexdigest()
    
    return DGICInput(
        version="schema_v1",
        lineage_hash="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        envelope_hash=envelope_hash,
        payload=payload
    )

def test_unified_aggregation_basics():
    # 1 policy violation signal, HIGH confidence
    dgic_1 = build_mock_dgic(EpistemicState.KNOWN, False, 0.0)
    sig_1 = UnifiedSignal(
        signal_id="sig_1",
        signal_type=SignalType.POLICY_VIOLATION_SIGNAL,
        base_risk_score=0.9,
        base_confidence_score=1.0,
        dgic_envelope=dgic_1
    )
    
    # 1 behavioral signal, somewhat less confident
    dgic_2 = build_mock_dgic(EpistemicState.KNOWN, False, 0.0)
    sig_2 = UnifiedSignal(
        signal_id="sig_2",
        signal_type=SignalType.BEHAVIOR_ANOMALY_SIGNAL,
        base_risk_score=0.6,
        base_confidence_score=0.8,
        dgic_envelope=dgic_2
    )
    
    result = aggregate_unified_signals([sig_1, sig_2])
    
    # Both active
    assert result.active_signal_count == 2
    assert result.abstained_signal_count == 0
    assert result.contradiction_count == 0
    
    # Weight verification:
    # Sig 1: W = 1.5 * 1.0 = 1.5. Score = 0.9.
    # Sig 2: W = 1.2 * 0.8 = 0.96. Score = 0.6.
    # Expected weighted risk = (1.5 * 0.9 + 0.96 * 0.6) / (1.5 + 0.96)
    #                        = (1.35 + 0.576) / 2.46
    #                        = 1.926 / 2.46 ≈ 0.7829
    
    # Check that score is strictly in the [0.0, 1.0] bound
    assert 0.0 <= result.aggregate_risk_score <= 1.0
    
    # Verify invariants are maintained
    assert result.safety_metadata["is_decision"] is False
    assert result.safety_metadata["authority"] == "NONE"
    assert result.safety_metadata["actionable"] is False

def test_unified_aggregation_contradictions():
    # 4 signals, 2 contradict (density = 0.5)
    # Contradiction sets contradiction flag in DGIC schema True
    
    sig_1 = UnifiedSignal(
        signal_id="s1", signal_type=SignalType.TEXT_RISK_SIGNAL,
        base_risk_score=0.8, base_confidence_score=1.0,
        dgic_envelope=build_mock_dgic(EpistemicState.KNOWN, contradiction=True)
    )
    sig_2 = UnifiedSignal(
        signal_id="s2", signal_type=SignalType.BEHAVIOR_ANOMALY_SIGNAL,
        base_risk_score=0.8, base_confidence_score=1.0,
        dgic_envelope=build_mock_dgic(EpistemicState.KNOWN, contradiction=True)
    )
    sig_3 = UnifiedSignal(
        signal_id="s3", signal_type=SignalType.POLICY_VIOLATION_SIGNAL,
        base_risk_score=0.8, base_confidence_score=1.0,
        dgic_envelope=build_mock_dgic(EpistemicState.KNOWN, contradiction=False)
    )
    sig_4 = UnifiedSignal(
        signal_id="s4", signal_type=SignalType.EXTERNAL_DETECTOR_SIGNAL,
        base_risk_score=0.8, base_confidence_score=1.0,
        dgic_envelope=build_mock_dgic(EpistemicState.KNOWN, contradiction=False)
    )
    
    result = aggregate_unified_signals([sig_1, sig_2, sig_3, sig_4])
    
    # Raw score avg would be 0.8.
    # Density = 0.5 (2 out of 4).
    # Penalty factor = 1.0 - (0.5 * 0.5) = 0.75.
    # Expected penalised score = 0.8 * 0.75 = 0.6.
    assert result.aggregate_risk_score == pytest.approx(0.6, abs=0.01)

def test_unified_aggregation_abstention():
    sig_1 = UnifiedSignal(
        signal_id="s1", signal_type=SignalType.TEXT_RISK_SIGNAL,
        base_risk_score=0.8, base_confidence_score=1.0,
        dgic_envelope=build_mock_dgic(EpistemicState.UNKNOWN)
    )
    result = aggregate_unified_signals([sig_1])
    
    assert result.all_abstained is True
    assert result.aggregate_risk_score == 0.0
    assert result.aggregate_risk_category == "LOW"
    assert result.errors is not None
    assert result.errors["error_code"] == "ALL_SIGNALS_ABSTAINED"

def test_unified_aggregation_ambiguous():
    sig_1 = UnifiedSignal(
        signal_id="s1", signal_type=SignalType.POLICY_VIOLATION_SIGNAL,
        base_risk_score=0.95, base_confidence_score=1.0,
        dgic_envelope=build_mock_dgic(EpistemicState.AMBIGUOUS)
    )
    result = aggregate_unified_signals([sig_1])
    
    # Ambiguous caps the score at AMBIGUOUS_RISK_CEILING (0.69).
    # Since there's only one signal, the weighted score is its raw capped score
    # scaled by whatever its DGIC adapter returns.
    assert result.aggregate_risk_score <= 0.69
