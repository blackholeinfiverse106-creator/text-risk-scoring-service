import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.contract_enforcement import validate_input_contract, ContractViolation

class TestForbiddenUsage:
    
    def test_reject_enforcement_role(self):
        """M-01: System must reject 'role: enforcement'"""
        payload = {
            "text": "some content",
            "context": {
                "caller_id": "bot-1",
                "role": "enforcement"
            }
        }
        
        with pytest.raises(ContractViolation) as excinfo:
            validate_input_contract(payload)
        
        assert "FORBIDDEN_ROLE" in str(excinfo.value)
        assert "strictly prohibited" in str(excinfo.value)

    def test_reject_decision_maker_role(self):
        """M-01: System must reject 'role: decision_maker'"""
        payload = {
            "text": "some content",
            "context": {
                "role": "decision_maker"
            }
        }
        
        with pytest.raises(ContractViolation) as excinfo:
            validate_input_contract(payload)
            
        assert "FORBIDDEN_ROLE" in str(excinfo.value)

    def test_reject_decision_injection(self):
        """M-02: System must reject decision-related fields"""
        forbidden_fields = ["action", "decision", "execute", "perform_action", "override_risk"]
        
        for field in forbidden_fields:
            payload = {
                "text": "some content",
                "context": {
                    field: "true"
                }
            }
            
            with pytest.raises(ContractViolation) as excinfo:
                validate_input_contract(payload)
                
            assert "DECISION_INJECTION" in str(excinfo.value)
            assert field in str(excinfo.value)

    def test_allowed_roles(self):
        """System should allow benign roles"""
        payload = {
            "text": "some content",
            "context": {
                "role": "moderator_assistant",
                "use_case": "triage"
            }
        }
        # Should not raise exception
        result = validate_input_contract(payload)
        assert result == "some content"

    def test_forbidden_top_level_field(self):
        """Generic check: extra top-level fields still forbidden"""
        payload = {
            "text": "content",
            "role": "enforcement"  # Top level, not context
        }
        
        with pytest.raises(ContractViolation) as excinfo:
            validate_input_contract(payload)
        
        assert "FORBIDDEN_FIELD" in str(excinfo.value)

if __name__ == "__main__":
    pytest.main([__file__])
