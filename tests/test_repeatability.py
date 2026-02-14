import hashlib
import json
import pytest
from app.engine import analyze_text

TEST_INPUTS = [
    "safe text here",
    "this is a scam",
    "violence and kill",
    "",
    "A" * 5000,
    "UPPERCASE SCAM",
    "mix of hack and drugs",
]

@pytest.mark.parametrize("text", TEST_INPUTS)
def test_repeatability_convergence(text):
    """
    Verify that 100 repeated executions on the same input yield bit-identical responses.
    """
    responses = []
    for _ in range(100):
        res = analyze_text(text)
        # Use sort_keys=True to ensure JSON string stability
        res_json = json.dumps(res, sort_keys=True)
        responses.append(hashlib.sha256(res_json.encode()).hexdigest())
    
    # Assert that all hashes are identical (set length is 1)
    assert len(set(responses)) == 1

def test_type_stability():
    """
    Ensure the returned data types are consistent.
    """
    res = analyze_text("test")
    assert isinstance(res["risk_score"], float)
    assert isinstance(res["confidence_score"], float)
    assert isinstance(res["risk_category"], str)
    assert isinstance(res["trigger_reasons"], list)
    assert isinstance(res["safety_metadata"], dict)
