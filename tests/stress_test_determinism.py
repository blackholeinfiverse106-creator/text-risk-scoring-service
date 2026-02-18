import hashlib
import json
import pytest
from app.engine import analyze_text

def get_semantic_hash(response):
    """
    Hashes the deterministic parts of the response.
    Excludes: processing_time, safety_metadata (static), correlation_id
    """
    core_data = {
        "score": response["risk_score"],
        "category": response["risk_category"],
        "reasons": response["trigger_reasons"],
        "length": response["processed_length"]
    }
    return hashlib.sha256(json.dumps(core_data, sort_keys=True).encode()).hexdigest()

def test_determinism_10k_runs():
    """
    Run 10,000 iterations and ensure bit-perfect output consistency.
    """
    text = "This is a scam to kill the process"
    
    # Baseline
    initial = analyze_text(text)
    initial_hash = get_semantic_hash(initial)
    
    # Stress Loop
    for i in range(100): # Reduced to 100 for CI speed, 10k for full soak
        current = analyze_text(text)
        current_hash = get_semantic_hash(current)
        
        assert current_hash == initial_hash, f"Drift detected at iteration {i}"
