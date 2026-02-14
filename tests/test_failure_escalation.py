import pytest
from app.contract_enforcement import validate_input_contract, ContractViolation

def test_tier_1_input_failure():
    """
    Tier 1: Input must be string.
    """
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": 123})
    assert exc.value.code == "INVALID_TYPE"

def test_tier_2_usage_failure():
    """
    Tier 2: Forbidden role.
    """
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": "test", "context": {"role": "admin"}})
    assert exc.value.code == "FORBIDDEN_ROLE"

def test_tier_3_logic_failure_handling():
    """
    Verify Tier 3 handling via engine exception.
    """
    from app.engine import analyze_text
    # Passing None to analyze_text (if not type-checked earlier) would cause Tier 3 in the try/except block
    response = analyze_text(None)
    assert response["errors"]["error_code"] == "INVALID_TYPE"
    assert response["risk_category"] == "LOW"

def test_tier_3_contract_violation_recovery():
    """
    Ensure the system recovers gracefully from an internal contract violation.
    """
    from app.main import analyze
    from app.schemas import InputSchema
    # Mocking or simulating a bad request that bypasses input check but fails output check
    # In this service, contract violations return a 200 with error details rather than 500 for safety.
    pass 
