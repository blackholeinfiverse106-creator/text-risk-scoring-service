import pytest
import random
import string
from app.engine import analyze_text, RISK_KEYWORDS

def random_string(length=50):
    return ''.join(random.choices(string.ascii_letters + string.digits + " ", k=length))

def test_score_invariants():
    """
    Property: For ANY input string S, 0.0 <= RiskScore(S) <= 1.0
    """
    for _ in range(100): # Fuzzing lite
        text = random_string(random.randint(0, 5000))
        # Inject some known keywords to ensure non-zero scores too
        if random.random() < 0.5:
            text += " kill scam"
            
        res = analyze_text(text)
        
        assert 0.0 <= res["risk_score"] <= 1.0, f"Score out of bounds for input: {text[:20]}..."
        assert res["risk_category"] in {"LOW", "MEDIUM", "HIGH"}

def test_statelessness_invariant():
    """
    Property: Analyze(S) is pure. 
    Global state (RISK_KEYWORDS) must NOT change.
    """
    initial_hash = str(RISK_KEYWORDS) # Simple string hash
    
    analyze_text("mutation test")
    
    final_hash = str(RISK_KEYWORDS)
    assert initial_hash == final_hash, "Global RISK_KEYWORDS mutated during execution!"

def test_non_null_invariant():
    """
    Property: Analyze(S) never returns None.
    """
    assert analyze_text("") is not None
    assert analyze_text("   ") is not None
    assert analyze_text(None) is not None # Logic handles non-string via error_response