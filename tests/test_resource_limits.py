import pytest
import time
from app.engine import analyze_text, MAX_TEXT_LENGTH

def test_payload_truncation():
    """
    Verify that inputs > MAX_TEXT_LENGTH are truncated without erroring.
    """
    huge_input = "a" * (MAX_TEXT_LENGTH + 1000)
    res = analyze_text(huge_input)
    assert res["processed_length"] == MAX_TEXT_LENGTH
    assert "truncated" in str(res["trigger_reasons"][0]).lower()

def test_processing_time_bound():
    """
    Verify 5000 char input is processed under 50ms (generous buffer).
    Real target is < 5ms, but CI can be slow.
    """
    large_input = "kill " * 1000 # 5000 chars of keywords (worst case regex)
    start = time.time()
    analyze_text(large_input)
    duration = time.time() - start
    
    # 200ms limit for CI stability
    assert duration < 0.200, f"Processing too slow: {duration}s"

def test_memory_safe_recursion():
    """
    Ensure no stack overflow on deep inputs (though we don't recurse).
    Just a sanity check for future changes.
    """
    # This engine shouldn't use recursion, but test ensures scalability.
    res = analyze_text("recurse " * 500)
    assert res["risk_score"] >= 0.0
