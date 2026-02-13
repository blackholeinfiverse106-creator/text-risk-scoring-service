import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app.engine import analyze_text, error_response

def test_safety_metadata_on_valid_input():
    """Verify safety metadata is strictly enforced on valid predictions."""
    result = analyze_text("kill kill kill") # High risk input
    
    metadata = result.get("safety_metadata")
    assert metadata is not None
    assert metadata["is_decision"] is False
    assert metadata["authority"] == "NONE"
    assert metadata["actionable"] is False

def test_safety_metadata_on_empty_input():
    """Verify safety metadata is strictly enforced on errors (Empty Input)."""
    result = analyze_text("")
    
    metadata = result.get("safety_metadata")
    assert metadata is not None
    assert metadata["is_decision"] is False
    assert metadata["authority"] == "NONE"
    assert metadata["actionable"] is False

def test_safety_metadata_on_invalid_type():
    """Verify safety metadata is strictly enforced on errors (Invalid Type)."""
    result = analyze_text(123) # type: ignore
    
    metadata = result.get("safety_metadata")
    assert metadata is not None
    assert metadata["is_decision"] is False
    assert metadata["authority"] == "NONE"
    assert metadata["actionable"] is False

def test_no_decision_fields_present():
    """Verify that no suppressed fields like 'decision' or 'verdict' leak into the response."""
    result = analyze_text("safe text")
    
    forbidden_keys = ["decision", "verdict", "action", "outcome", "block", "ban"]
    for key in forbidden_keys:
        assert key not in result, f"Forbidden key '{key}' found in response!"

def test_contract_immutability():
    """Verify that even with maximum risk score, is_decision remains False."""
    # Construct input to maximize score (needs multiple unique keywords)
    # We need enough keywords to hit the cap.
    # Violence has many keywords.
    text = "kill murder attack assault stab shoot bomb terror gun knife beat dead execution"
    result = analyze_text(text)
    
    # Verify we hit the high score range
    assert result["risk_score"] >= 0.7
    assert result["risk_category"] == "HIGH"
    
    # The Contract: Even at 100% risk, it is NOT a decision.
    assert result["safety_metadata"]["is_decision"] is False
    assert result["safety_metadata"]["actionable"] is False

def test_error_response_helper_compliance():
    """Verify the error helper function also complies with the contract."""
    # Direct call to helper
    res = error_response("TEST_CODE", "Test message")
    assert res["safety_metadata"]["is_decision"] is False
