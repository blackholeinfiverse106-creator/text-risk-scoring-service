import pytest
import time
from app.engine import analyze_text, MAX_TEXT_LENGTH

def test_obfuscation_resistance_basic():
    """
    Ensure basic normalization (case) works.
    Note: A single keyword match (0.2) is LOW risk (< 0.3 threshold).
    """
    response = analyze_text("SCAM")
    assert response["risk_category"] == "LOW"
    assert response["risk_score"] == 0.2

def test_bypass_attempt_phonetic():
    """
    Document current limitation: phonetic bypasses are NOT caught by simple keywords.
    """
    response = analyze_text("kylling")
    # This is a known limitation specified in misuse-guide.md
    assert response["risk_category"] == "LOW"

def test_obfuscation_dots_limitation():
    """
    Document current limitation: dot-separated obfuscation.
    """
    response = analyze_text("s.c.a.m")
    assert response["risk_category"] == "LOW"

def test_decision_injection_rejection_logic():
    """
    Verify that the system rejects context fields that imply agency.
    """
    from app.contract_enforcement import validate_input_contract, ContractViolation
    bad_payload = {
        "text": "threat",
        "context": {"override_risk": 0.0}
    }
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract(bad_payload)
    assert exc.value.code == "DECISION_INJECTION"
