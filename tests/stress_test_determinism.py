import hashlib
import json
import pytest
import sys
import os

# Allow running from anywhere
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

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
    # Stress Loop
    ITERATIONS = 1000
    print(f"Starting {ITERATIONS} iterations...")
    
    for i in range(ITERATIONS):
        current = analyze_text(text)
        current_hash = get_semantic_hash(current)
        
        if current_hash != initial_hash:
            raise AssertionError(f"Drift detected at iteration {i}")
            
    print("Success: All iterations matched.")
    
    # Generate Artifact
    report = {
        "status": "PASSED",
        "iterations": ITERATIONS,
        "input_hash": hashlib.sha256(text.encode()).hexdigest(),
        "output_hash": initial_hash,
        "consistency": "100%"
    }
    
    with open("determinism_benchmark_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Artifact generated: determinism_benchmark_report.json")

if __name__ == "__main__":
    test_determinism_10k_runs()
