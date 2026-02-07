"""
Contract Enforcement Tests
Validates all contract boundaries and invalid input handling
"""
import pytest
from app.contract_enforcement import validate_input_contract, validate_output_contract, ContractViolation
from app.engine import analyze_text

class TestInputContractEnforcement:
    """Test input contract validation"""
    
    def test_valid_input_passes(self):
        """Valid input should pass validation"""
        valid_input = {"text": "hello world"}
        result = validate_input_contract(valid_input)
        assert result == "hello world"
    
    def test_missing_text_field_rejected(self):
        """Missing 'text' field should be rejected"""
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({})
        assert exc.value.code == "MISSING_FIELD"
    
    def test_forbidden_fields_rejected(self):
        """Extra fields should be rejected"""
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": "hello", "extra": "forbidden"})
        assert exc.value.code == "FORBIDDEN_FIELD"
    
    def test_invalid_type_rejected(self):
        """Non-string text should be rejected"""
        invalid_inputs = [
            {"text": 123},
            {"text": True},
            {"text": []},
            {"text": {}},
            {"text": None}
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises(ContractViolation) as exc:
                validate_input_contract(invalid_input)
            assert exc.value.code == "INVALID_TYPE"
    
    def test_non_dict_request_rejected(self):
        """Non-dict requests should be rejected"""
        invalid_requests = ["string", 123, [], True, None]
        
        for invalid_request in invalid_requests:
            with pytest.raises(ContractViolation) as exc:
                validate_input_contract(invalid_request)
            assert exc.value.code == "INVALID_REQUEST"

class TestOutputContractEnforcement:
    """Test output contract validation"""
    
    def test_valid_output_passes(self):
        """Valid output should pass validation"""
        valid_output = {
            "risk_score": 0.5,
            "confidence_score": 0.8,
            "risk_category": "MEDIUM",
            "trigger_reasons": ["test reason"],
            "processed_length": 10,
            "safety_metadata": {
                "is_decision": False,
                "authority": "NONE",
                "actionable": False
            },
            "errors": None
        }
        validate_output_contract(valid_output)  # Should not raise
    
    def test_missing_required_fields_rejected(self):
        """Missing required fields should be rejected"""
        incomplete_output = {
            "risk_score": 0.5,
            "risk_category": "LOW"
            # Missing other required fields
        }
        
        with pytest.raises(ContractViolation) as exc:
            validate_output_contract(incomplete_output)
        assert exc.value.code == "MISSING_OUTPUT_FIELD"
    
    def test_forbidden_output_fields_rejected(self):
        """Extra output fields should be rejected"""
        output_with_extra = {
            "risk_score": 0.5,
            "confidence_score": 0.8,
            "risk_category": "MEDIUM",
            "trigger_reasons": [],
            "processed_length": 10,
            "safety_metadata": {
                "is_decision": False,
                "authority": "NONE",
                "actionable": False
            },
            "errors": None,
            "extra_field": "forbidden"
        }
        
        with pytest.raises(ContractViolation) as exc:
            validate_output_contract(output_with_extra)
        assert exc.value.code == "FORBIDDEN_OUTPUT_FIELD"
    
    def test_invalid_risk_score_rejected(self):
        """Invalid risk scores should be rejected"""
        base_output = {
            "risk_score": 0.5,
            "confidence_score": 0.8,
            "risk_category": "MEDIUM",
            "trigger_reasons": [],
            "processed_length": 10,
            "safety_metadata": {
                "is_decision": False,
                "authority": "NONE",
                "actionable": False
            },
            "errors": None
        }
        
        # Test invalid types
        invalid_scores = ["0.5", True, [], {}]
        for invalid_score in invalid_scores:
            output = base_output.copy()
            output["risk_score"] = invalid_score
            with pytest.raises(ContractViolation) as exc:
                validate_output_contract(output)
            assert exc.value.code == "INVALID_RISK_SCORE_TYPE"
        
        # Test invalid ranges
        invalid_ranges = [-0.1, 1.1, 999]
        for invalid_range in invalid_ranges:
            output = base_output.copy()
            output["risk_score"] = invalid_range
            with pytest.raises(ContractViolation) as exc:
                validate_output_contract(output)
            assert exc.value.code == "INVALID_RISK_SCORE_RANGE"
    
    def test_invalid_risk_category_rejected(self):
        """Invalid risk categories should be rejected"""
        base_output = {
            "risk_score": 0.5,
            "confidence_score": 0.8,
            "risk_category": "MEDIUM",
            "trigger_reasons": [],
            "processed_length": 10,
            "safety_metadata": {
                "is_decision": False,
                "authority": "NONE",
                "actionable": False
            },
            "errors": None
        }
        
        # Test invalid types
        invalid_types = [123, True, [], {}]
        for invalid_type in invalid_types:
            output = base_output.copy()
            output["risk_category"] = invalid_type
            with pytest.raises(ContractViolation) as exc:
                validate_output_contract(output)
            assert exc.value.code == "INVALID_RISK_CATEGORY_TYPE"
        
        # Test invalid values
        invalid_values = ["INVALID", "high", "medium", ""]
        for invalid_value in invalid_values:
            output = base_output.copy()
            output["risk_category"] = invalid_value
            with pytest.raises(ContractViolation) as exc:
                validate_output_contract(output)
            assert exc.value.code == "INVALID_RISK_CATEGORY_VALUE"
    
    def test_invalid_trigger_reasons_rejected(self):
        """Invalid trigger reasons should be rejected"""
        base_output = {
            "risk_score": 0.5,
            "confidence_score": 0.8,
            "risk_category": "MEDIUM",
            "trigger_reasons": [],
            "processed_length": 10,
            "safety_metadata": {
                "is_decision": False,
                "authority": "NONE",
                "actionable": False
            },
            "errors": None
        }
        
        # Test invalid type
        output = base_output.copy()
        output["trigger_reasons"] = "not an array"
        with pytest.raises(ContractViolation) as exc:
            validate_output_contract(output)
        assert exc.value.code == "INVALID_TRIGGER_REASONS_TYPE"
        
        # Test invalid element types
        output = base_output.copy()
        output["trigger_reasons"] = ["valid", 123, "also valid"]
        with pytest.raises(ContractViolation) as exc:
            validate_output_contract(output)
        assert exc.value.code == "INVALID_TRIGGER_REASON_TYPE"
    
    def test_invalid_errors_rejected(self):
        """Invalid error objects should be rejected"""
        base_output = {
            "risk_score": 0.5,
            "confidence_score": 0.8,
            "risk_category": "MEDIUM",
            "trigger_reasons": [],
            "processed_length": 10,
            "safety_metadata": {
                "is_decision": False,
                "authority": "NONE",
                "actionable": False
            },
            "errors": None
        }
        
        # Test invalid error type
        output = base_output.copy()
        output["errors"] = "not an object"
        with pytest.raises(ContractViolation) as exc:
            validate_output_contract(output)
        assert exc.value.code == "INVALID_ERRORS_TYPE"
        
        # Test invalid error structure
        output = base_output.copy()
        output["errors"] = {"wrong_field": "value"}
        with pytest.raises(ContractViolation) as exc:
            validate_output_contract(output)
        assert exc.value.code == "INVALID_ERROR_STRUCTURE"
        
        # Test invalid error code
        output = base_output.copy()
        output["errors"] = {"error_code": "INVALID_CODE", "message": "test"}
        with pytest.raises(ContractViolation) as exc:
            validate_output_contract(output)
        assert exc.value.code == "INVALID_ERROR_CODE_VALUE"

class TestInvalidInputMatrix:
    """Test the complete invalid input matrix"""
    
    def test_null_input_produces_deterministic_error(self):
        """Null input should produce INVALID_TYPE error"""
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": None})
        assert exc.value.code == "INVALID_TYPE"
        assert "string" in exc.value.message
    
    def test_number_input_produces_deterministic_error(self):
        """Number input should produce INVALID_TYPE error"""
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": 123})
        assert exc.value.code == "INVALID_TYPE"
    
    def test_boolean_input_produces_deterministic_error(self):
        """Boolean input should produce INVALID_TYPE error"""
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": True})
        assert exc.value.code == "INVALID_TYPE"
    
    def test_array_input_produces_deterministic_error(self):
        """Array input should produce INVALID_TYPE error"""
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": []})
        assert exc.value.code == "INVALID_TYPE"
    
    def test_object_input_produces_deterministic_error(self):
        """Object input should produce INVALID_TYPE error"""
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": {}})
        assert exc.value.code == "INVALID_TYPE"
    
    def test_empty_string_handled_by_engine(self):
        """Empty string should pass contract validation but be handled by engine"""
        result = validate_input_contract({"text": ""})
        assert result == ""
        
        # Engine should handle empty input
        response = analyze_text("")
        assert response["errors"]["error_code"] == "EMPTY_INPUT"
    
    def test_whitespace_only_handled_by_engine(self):
        """Whitespace-only string should be handled by engine"""
        result = validate_input_contract({"text": "   "})
        assert result == "   "
        
        # Engine should handle empty input after normalization
        response = analyze_text("   ")
        assert response["errors"]["error_code"] == "EMPTY_INPUT"
    
    def test_excessive_length_handled_by_engine(self):
        """Excessive length should pass contract but be handled by engine"""
        long_text = "a" * 6000
        result = validate_input_contract({"text": long_text})
        assert result == long_text
        
        # Engine should handle truncation
        response = analyze_text(long_text)
        assert response["processed_length"] == 5000
        assert any("truncated" in reason.lower() for reason in response["trigger_reasons"])

class TestEndToEndContractEnforcement:
    """Test complete contract enforcement through the system"""
    
    def test_valid_request_produces_valid_response(self):
        """Valid request should produce contract-compliant response"""
        response = analyze_text("hello world")
        validate_output_contract(response)  # Should not raise
    
    def test_error_responses_are_contract_compliant(self):
        """All error responses should be contract compliant"""
        error_inputs = [
            "",  # EMPTY_INPUT
            123,  # INVALID_TYPE (handled at API layer)
            "a" * 6000,  # Truncation case
        ]
        
        for error_input in error_inputs:
            if isinstance(error_input, str):
                response = analyze_text(error_input)
                validate_output_contract(response)  # Should not raise
    
    def test_deterministic_error_responses(self):
        """Same invalid input should produce same error response"""
        response1 = analyze_text("")
        response2 = analyze_text("")
        assert response1 == response2
        assert response1["errors"]["error_code"] == "EMPTY_INPUT"