import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app.engine import analyze_text, MAX_TEXT_LENGTH

def test_determinism_simple():
    """Verify that the same input always yields the same result."""
    text = "This is a test with violence and fraud."
    result1 = analyze_text(text)
    result2 = analyze_text(text)
    
    assert result1 == result2

def test_determinism_complex():
    """Verify determinism with multiple runs."""
    text = "shoot kill scam money"
    results = [analyze_text(text) for _ in range(50)]
    first = results[0]
    for res in results[1:]:
        assert res == first

def test_invariant_score_bounds():
    """INV-01: Score must be between 0.0 and 1.0"""
    # Generate a very high risk text
    text = "kill " * 100 + " scam " * 100 + " bomb " * 100
    result = analyze_text(text)
    assert 0.0 <= result["risk_score"] <= 1.0

def test_invariant_category_consistency():
    """INV-04: Category mapping must match score ranges."""
    # Test Low
    res_low = analyze_text("hello world")
    if res_low["risk_score"] < 0.3:
        assert res_low["risk_category"] == "LOW"
    
    # Test Medium (needs manual tuning to hit range 0.3-0.7)
    # 2 keywords = 0.4 score.
    res_med = analyze_text("kill kill") 
    # 0.2 + 0.2 = 0.4
    if 0.3 <= res_med["risk_score"] < 0.7:
        assert res_med["risk_category"] == "MEDIUM"

    # Test High
    res_high = analyze_text("kill " * 10)
    if res_high["risk_score"] >= 0.7:
        assert res_high["risk_category"] == "HIGH"

def test_forbidden_state_high_score_low_category():
    """F-2: High Score but Low Category is forbidden."""
    # We can't easily force this without mocking, but we verify it doesn't happen naturally.
    result = analyze_text("kill " * 50)
    assert not (result["risk_score"] >= 0.7 and result["risk_category"] == "LOW")

def test_forbidden_state_low_score_high_category():
    """F-3: Low Score but High Category is forbidden."""
    result = analyze_text("hello")
    assert not (result["risk_score"] < 0.3 and result["risk_category"] == "HIGH")

def test_forbidden_state_empty_reasons_with_score():
    """F-4: Reasons must be present if score > 0."""
    result = analyze_text("kill")
    if result["risk_score"] > 0:
        assert len(result["trigger_reasons"]) > 0

def test_rule_evaluation_order_implicit():
    """
    Indirectly test evaluation order by ensuring the 'trigger_reasons' are
    always returned in the same order (Alphabetical categories).
    Input touches 'violence'(V) and 'fraud'(F).
    Order should be Fraud then Violence (F < V).
    """
    text = "kill scam"
    result = analyze_text(text)
    reasons = result["trigger_reasons"]
    # We expect "Detected fraud keyword..." then "Detected violence keyword..."
    # or vice versa depending on implementation.
    # The requirement is that it is *consistent*.
    
    fraud_idx = -1
    violence_idx = -1
    
    for i, r in enumerate(reasons):
        if "fraud" in r:
            fraud_idx = i
        elif "violence" in r:
            violence_idx = i
            
    assert fraud_idx != -1
    assert violence_idx != -1
    # If we enforce alphabetical key order: fraud < violence
    assert fraud_idx < violence_idx
