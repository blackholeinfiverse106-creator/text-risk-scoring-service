#!/usr/bin/env python3
"""
Determinism validation script
Run this to verify deterministic behavior
"""

import hashlib
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
    
    for i, test_input in enumerate(test_cases):
        print(f"Test {i+1}: {repr(test_input)[:50]}...")
        
        # Run 100 times
        results = []
        for _ in range(100):
            result = analyze_text(test_input)
            result_hash = hashlib.sha256(
                json.dumps(result, sort_keys=True).encode()
            ).hexdigest()
            results.append(result_hash)
        
        # Verify all hashes are identical
        unique_hashes = set(results)
        if len(unique_hashes) == 1:
            print(f"  PASS - All 100 executions identical")
        else:
            print(f"  FAIL - Found {len(unique_hashes)} different outputs")
            return False
    
    print("\nAll determinism tests passed!")
    return True

if __name__ == "__main__":
    validate_determinism()