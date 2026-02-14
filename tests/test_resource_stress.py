import pytest
import time
import uuid
from app.engine import analyze_text, MAX_TEXT_LENGTH

def test_large_payload_performance():
    """
    Verify that the system handles maximum length payload within acceptable time limits.
    """
    large_text = "scam" * 1250  # 4 * 1250 = 5000 characters
    
    start_time = time.time()
    response = analyze_text(large_text)
    duration = time.time() - start_time
    
    assert response["processed_length"] == MAX_TEXT_LENGTH
    # Truncation logic applies if length >= MAX_TEXT_LENGTH after strip
    # In this case exactly 5000
    assert response["processed_length"] <= MAX_TEXT_LENGTH

def test_concurrency_stability():
    """
    Rapid-fire execution to test for state leakage or memory buildup.
    """
    for _ in range(50):
        text = f"test alert {uuid.uuid4()}"
        res = analyze_text(text)
        assert res["errors"] is None

def test_empty_string_safety():
    """
    Verify empty input doesn't trigger division by zero or other math errors.
    """
    response = analyze_text("")
    assert response["errors"]["error_code"] == "EMPTY_INPUT"
