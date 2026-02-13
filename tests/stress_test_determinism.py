import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import hashlib
import json
import logging
from app.engine import analyze_text

# Configure logging
logging.basicConfig(level=logging.ERROR) # Only show errors during stress test

INPUTS = [
    "Simple valid text",
    "kill " * 100, # Repeat high risk
    "", # Empty
    "fraud scam money", # Mixed
    "A" * 6000, # Truncation case
    "Hello world", # Low risk
]

ITERATIONS = 1000

def get_hash(result: dict) -> str:
    """Compute deterministic hash of the result dictionary."""
    # Sort keys to ensure JSON serialization is deterministic
    serialized = json.dumps(result, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()

def run_stress_test():
    print(f"Starting Determinism Stress Test: {ITERATIONS} runs per input...")
    
    start_global = time.time()
    errors = 0
    
    for i, text in enumerate(INPUTS):
        print(f"Testing Input {i+1}/{len(INPUTS)}: '{text[:20]}...'")
        
        # Baseline run
        baseline = analyze_text(text)
        baseline_hash = get_hash(baseline)
        
        for run in range(ITERATIONS):
            result = analyze_text(text)
            current_hash = get_hash(result)
            
            if current_hash != baseline_hash:
                print(f"FATAL: Divergence detected on run {run} for input '{text[:20]}...'")
                print(f"Baseline: {baseline}")
                print(f"Current:  {result}")
                errors += 1
                break
                
    total_time = time.time() - start_global
    print("-" * 40)
    print(f"Completed in {total_time:.2f}s")
    
    if errors == 0:
        print("SUCCESS: 100% Determinism Proven.")
    else:
        print(f"FAILURE: {errors} divergences found.")
        exit(1)

if __name__ == "__main__":
    run_stress_test()
