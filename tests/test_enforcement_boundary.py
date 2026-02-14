import pytest
from app.contract_enforcement import validate_input_contract, validate_output_contract, ContractViolation

def test_forbidden_role_rejection():
    """
    Ensure that requests from enforcement or admin roles are rejected.
    """
    bad_input = {
        "text": "some text",
        "context": {"role": "admin"}
    }
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract(bad_input)
    assert "FORBIDDEN_ROLE" in str(exc.value)

def test_decision_injection_rejection():
    """
    Ensure that inputs containing decision fields (action, execute) are rejected.
    """
    bad_input = {
        "text": "some text",
        "context": {"action": "delete_user"}
    }
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract(bad_input)
    assert "DECISION_INJECTION" in str(exc.value)

def test_output_authority_enforcement():
    """
    Ensure that any attempt to return a 'True' authority flag is caught.
    """
    bad_output = {
        "risk_score": 0.5,
        "confidence_score": 0.8,
        "risk_category": "MEDIUM",
        "trigger_reasons": ["test"],
        "processed_length": 4,
        "safety_metadata": {
            "is_decision": True,  # ILLEGAL
            "authority": "NONE",
            "actionable": False
        },
        "errors": None
    }
    with pytest.raises(ContractViolation) as exc:
        validate_output_contract(bad_output)
    assert "INVALID_IS_DECISION" in str(exc.value)

def test_non_authority_defaults():
    """
    Verify that the standard response model adheres to the non-authority layer.
    """
    from app.engine import analyze_text
    response = analyze_text("safe input")
    # Contract layer check
    validate_output_contract(response)
    # Value check
    assert response["safety_metadata"]["is_decision"] is False
    assert response["safety_metadata"]["authority"] == "NONE"
    assert response["safety_metadata"]["actionable"] is False
