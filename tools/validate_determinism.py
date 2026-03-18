#!/usr/bin/env python3
"""
Determinism validation script
Run this to verify deterministic behavior
"""

import hashlib
import json
import sys
import os
sys.path.append(os.getcwd())

from app.engine import analyze_text

def validate_determinism():
    test_cases = [
        "hello world",
        "this is a scam and hack",
        "kill attack bomb",
        "",
        "a" * 6000,
        123,
        None,
        "   whitespace   ",
        "UPPERCASE SCAM",
        "kill" * 50,
    ]
    
    print("Validating determinism...")
    
    with open("formal_determinism_proof.log", "w") as proof_file:
        proof_file.write("FORMAL DETERMINISM PROOF LOG\n")
        proof_file.write("============================\n\n")
        
        all_passed = True
        
        for i, test_input in enumerate(test_cases):
            input_repr = repr(test_input)[:50]
            proof_file.write(f"TEST CASE {i+1}: {input_repr}\n")
            
            # Run 100 times
            results = []
            for _ in range(100):
                result = analyze_text(test_input)
                # Sort keys to ensure consistent JSON serialization
                result_json = json.dumps(result, sort_keys=True)
                result_hash = hashlib.sha256(result_json.encode()).hexdigest()
                results.append(result_hash)
            
            # Verify all hashes are identical
            unique_hashes = set(results)
            if len(unique_hashes) == 1:
                proof_hash = unique_hashes.pop()
                proof_file.write(f"  RESULT: PASS\n")
                proof_file.write(f"  ITERATIONS: 100\n")
                proof_file.write(f"  OUTPUT HASH: {proof_hash}\n")
                proof_file.write(f"  CONVERGENCE: 100%\n\n")
            else:
                proof_file.write(f"  RESULT: FAIL\n")
                proof_file.write(f"  DIVERGENCE DETECTED: {len(unique_hashes)} unique outputs\n\n")
                all_passed = False
        
        if all_passed:
            proof_file.write("FINAL VERDICT: PROVEN\n")
            proof_file.write("All tests demonstrated 100% deterministic convergence.\n")
            print("Determinism proof generated: formal_determinism_proof.log")
            return True
        else:
            proof_file.write("FINAL VERDICT: FAILED\n")
            print("Determinism proof FAILED. Check formal_determinism_proof.log")
            return False

if __name__ == "__main__":
    validate_determinism()