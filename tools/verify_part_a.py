"""
Verification Script for PART A Completion
Tests that safety_metadata is present and enforced in all responses
"""

import sys
sys.path.insert(0, '.')

from app.engine import analyze_text
from app.contract_enforcement import validate_output_contract, ContractViolation

def test_safety_metadata_in_success():
    """Test that successful responses include safety_metadata"""
    result = analyze_text("This is a test message")
    
    assert "safety_metadata" in result, "Missing safety_metadata in success response"
    assert result["safety_metadata"]["is_decision"] is False, "is_decision must be False"
    assert result["safety_metadata"]["authority"] == "NONE", "authority must be 'NONE'"
    assert result["safety_metadata"]["actionable"] is False, "actionable must be False"
    
    print("[OK] Success response includes correct safety_metadata")

def test_safety_metadata_in_error():
    """Test that error responses include safety_metadata"""
    result = analyze_text("")  # Empty input triggers error
    
    assert "safety_metadata" in result, "Missing safety_metadata in error response"
    assert result["safety_metadata"]["is_decision"] is False, "is_decision must be False"
    assert result["safety_metadata"]["authority"] == "NONE", "authority must be 'NONE'"
    assert result["safety_metadata"]["actionable"] is False, "actionable must be False"
    assert result["errors"] is not None, "Should have error"
    
    print("[OK] Error response includes correct safety_metadata")

def test_contract_enforcement():
    """Test that contract validation enforces safety_metadata"""
    
    # Valid response should pass
    valid_response = {
        "risk_score": 0.5,
        "confidence_score": 0.8,
        "risk_category": "MEDIUM",
        "trigger_reasons": ["test"],
        "processed_length": 10,
        "safety_metadata": {
            "is_decision": False,
            "authority": "NONE",
            "actionable": False
        },
        "errors": None
    }
    
    try:
        validate_output_contract(valid_response)
        print("[OK] Valid response passes contract validation")
    except ContractViolation as e:
        print("[FAIL] Valid response failed: {e}")
        sys.exit(1)
    
    # Missing safety_metadata should fail
    invalid_response = {
        "risk_score": 0.5,
        "confidence_score": 0.8,
        "risk_category": "MEDIUM",
        "trigger_reasons": ["test"],
        "processed_length": 10,
        "errors": None
    }
    
    try:
        validate_output_contract(invalid_response)
        print("[FAIL] Missing safety_metadata should have failed validation")
        sys.exit(1)
    except ContractViolation:
        print("[OK] Missing safety_metadata correctly rejected")
    
    # Wrong authority value should fail
    wrong_authority = {
        "risk_score": 0.5,
        "confidence_score": 0.8,
        "risk_category": "MEDIUM",
        "trigger_reasons": ["test"],
        "processed_length": 10,
        "safety_metadata": {
            "is_decision": False,
            "authority": "FULL",  # Wrong value
            "actionable": False
        },
        "errors": None
    }
    
    try:
        validate_output_contract(wrong_authority)
        print("[FAIL] Wrong authority value should have failed validation")
        sys.exit(1)
    except ContractViolation:
        print("[OK] Wrong authority value correctly rejected")

def test_high_risk_content():
    """Test that even high-risk content includes safety_metadata"""
    result = analyze_text("kill murder attack bomb terrorist")
    
    assert result["risk_category"] == "HIGH", "Should be high risk"
    assert "safety_metadata" in result, "Missing safety_metadata in high-risk response"
    assert result["safety_metadata"]["is_decision"] is False, "Even high-risk is not a decision"
    assert result["safety_metadata"]["authority"] == "NONE", "Even high-risk has no authority"
    assert result["safety_metadata"]["actionable"] is False, "Even high-risk is not actionable"
    
    print("[OK] High-risk response correctly includes non-authority metadata")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PART A VERIFICATION - Safety Metadata Enforcement")
    print("="*60 + "\n")
    
    try:
        test_safety_metadata_in_success()
        test_safety_metadata_in_error()
        test_contract_enforcement()
        test_high_risk_content()
        
        print("\n" + "="*60)
        print("[SUCCESS] ALL TESTS PASSED - PART A IS COMPLETE")
        print("="*60 + "\n")
        
        print("Summary:")
        print("- safety_metadata present in all responses")
        print("- Non-authority values enforced (is_decision=False, authority=NONE)")
        print("- Contract validation rejects missing/incorrect metadata")
        print("- System cannot output executable decisions")
        print("\nPART A: Authority & Execution Boundary Formalization [COMPLETE]")
        
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
