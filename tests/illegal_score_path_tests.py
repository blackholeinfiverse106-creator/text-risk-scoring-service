import pytest
from app.engine import analyze_text

def test_illegal_score_bounds():
    """
    Impossible Path: Score cannot exceed 1.0 even with infinite keywords.
    """
    # Use distinct keywords to accumulate score. 
    # "kill" (violence) + "scam" (fraud) + "abuse" (abuse) + ...
    # We need enough distinct categories/keywords to theoretically exceed 1.0
    # Current weights: 0.2 per keyword. 
    # 6 distinct keywords = 1.2 raw score -> Clamped to 1.0
    text = "kill scam idiot porn cocaine terrorism"
    res = analyze_text(text)
    assert res["risk_score"] == 1.0
    assert res["risk_category"] == "HIGH"
    
def test_illegal_low_score_high_risk():
    """
    Impossible Path: Score < 0.3 but Risk = HIGH.
    This effectively tests the invariant correction logic if it were possible to trigger,
    but here we ensure the logic holds normally.
    """
    # "kill" = 0.2 -> LOW
    res = analyze_text("kill")
    assert res["risk_score"] == 0.2
    assert res["risk_category"] == "LOW"

def test_illegal_empty_reasons_with_score():
    """
    Impossible Path: Score > 0 but no reasons.
    """
    res = analyze_text("kill")
    assert res["risk_score"] > 0
    assert len(res["trigger_reasons"]) > 0

def test_zero_score_consistency():
    """
    Impossible Path: Score = 0 but Category != LOW.
    """
    res = analyze_text("hello world")
    assert res["risk_score"] == 0.0
    assert res["risk_category"] == "LOW"
    assert len(res["trigger_reasons"]) == 0
