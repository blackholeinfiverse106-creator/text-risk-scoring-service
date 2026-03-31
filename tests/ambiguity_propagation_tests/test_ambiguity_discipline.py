import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.layer3_dgic import (
    EpistemicState,
    DGICInput,
    DGICPayload,
    DGICContractViolation,
    validate_dgic_input,
    adapt_dgic,
    apply_dgic_modifiers,
    build_evidence_hash,
    compute_envelope_hash,
)

def _make_dgic(state: EpistemicState, collapse_flag: bool = False) -> DGICInput:
    evidence = build_evidence_hash(f"test_evidence_{state.value}_{collapse_flag}")
    payload = DGICPayload(
        epistemic_state=state,
        entropy_score=0.0,
        contradiction_flag=False,
    )
    payload_dict = {
        "epistemic_state": state.value,
        "entropy_score": 0.0,
        "contradiction_flag": False
    }
    envelope_hash = compute_envelope_hash("schema_v1", evidence, payload_dict)
    
    return DGICInput(
        version="schema_v1",
        lineage_hash=evidence,
        envelope_hash=envelope_hash,
        payload=payload,
        collapse_flag=collapse_flag,
    )

def test_illegal_collapse_attempt_is_blocked():
    """Verify that forcefully collapsing an AMBIGUOUS state is cryptographically rejected."""
    dgic = _make_dgic(EpistemicState.AMBIGUOUS, collapse_flag=True)
    with pytest.raises(DGICContractViolation, match="Illegal epistemic collapse: AMBIGUOUS state cannot be forcefully collapsed"):
        validate_dgic_input(dgic)

def test_ambiguous_propagation_maintains_warning():
    """Verify that AMBIGUOUS state propagates correctly, bounding risk and emitting warning."""
    dgic = _make_dgic(EpistemicState.AMBIGUOUS, collapse_flag=False)
    
    # 1. Validation should pass
    validate_dgic_input(dgic)
    
    # 2. Adaptation should bound risk
    adapted = adapt_dgic(dgic)
    assert adapted.scoring_mode == "RISK_BOUNDED"
    assert adapted.risk_ceiling == 0.69
    assert adapted.epistemic_warning is True
    
    # 3. Application should clamp high risk
    base_result = {
        "risk_score": 0.95,
        "confidence_score": 0.9,
        "risk_category": "HIGH"
    }
    final_result = apply_dgic_modifiers(base_result, adapted)
    
    assert final_result["risk_score"] == 0.69
    assert final_result["risk_category"] == "MEDIUM"
    assert final_result["dgic_metadata"]["epistemic_warning"] is True
    assert final_result["dgic_metadata"]["epistemic_state"] == "AMBIGUOUS"
    assert final_result["safety_metadata"]["authority"] == "NONE"
    assert final_result["safety_metadata"]["is_decision"] is False

def test_unknown_causes_abstention():
    """Verify that UNKNOWN state forces the system to abstain and zero the risk score."""
    dgic = _make_dgic(EpistemicState.UNKNOWN, collapse_flag=False)
    
    # 1. Validation should pass
    validate_dgic_input(dgic)
    
    # 2. Adaptation should signal abstention
    adapted = adapt_dgic(dgic)
    assert adapted.scoring_mode == "ABSTAIN"
    assert adapted.abstain is True
    assert adapted.epistemic_warning is True
    
    # 3. Application should zero the risk signal
    base_result = {
        "risk_score": 0.8,
        "confidence_score": 0.8,
        "risk_category": "HIGH"
    }
    final_result = apply_dgic_modifiers(base_result, adapted)
    
    assert final_result["risk_score"] == 0.0
    assert final_result["confidence_score"] == 0.0
    assert final_result["risk_category"] == "LOW"
    assert final_result["errors"]["error_code"] == "EPISTEMIC_ABSTENTION"
    assert final_result["dgic_metadata"]["epistemic_state"] == "UNKNOWN"
    assert final_result["safety_metadata"]["is_decision"] is False
