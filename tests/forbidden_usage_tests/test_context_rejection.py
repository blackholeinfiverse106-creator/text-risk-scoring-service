import pytest
from app.contract_enforcement import validate_input_contract, ContractViolation

def test_reject_admin_role():
    """
    Ensure inputs claiming 'admin' role are rejected.
    """
    payload = {
        "text": "regular content",
        "context": {"role": "admin"}
    }
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract(payload)
    assert exc.value.code == "FORBIDDEN_ROLE"

def test_reject_decision_request():
    """
    Ensure inputs requesting a specific decision/action are rejected.
    """
    payload = {
        "text": "scam content",
        "context": {"action": "ban_user"}
    }
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract(payload)
    assert exc.value.code == "DECISION_INJECTION"

def test_reject_risk_override():
    """
    Ensure inputs trying to force a score are rejected.
    """
    payload = {
        "text": "bad content",
        "context": {"override_risk": 0.0}
    }
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract(payload)
    assert exc.value.code == "DECISION_INJECTION"
