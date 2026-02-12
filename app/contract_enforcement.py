"""
Contract Enforcement Module
Validates all inputs and outputs against sealed contracts
"""
import json
from typing import Dict, Any, List, Union

# Contract constants (IMMUTABLE)
MAX_TEXT_LENGTH = 5000
MAX_TRIGGER_REASONS = 100
VALID_RISK_CATEGORIES = {"LOW", "MEDIUM", "HIGH"}
VALID_ERROR_CODES = {
    "INVALID_TYPE", "EMPTY_INPUT", "EXCESSIVE_LENGTH", 
    "INVALID_ENCODING", "FORBIDDEN_FIELD", "MISSING_FIELD", "INTERNAL_ERROR",
    "INVALID_CONTEXT", "FORBIDDEN_ROLE", "DECISION_INJECTION"
}

class ContractViolation(Exception):
    """Raised when contract is violated"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")

def validate_input_contract(data: Any) -> str:
    """
    Validates input against sealed contract.
    Returns the text string if valid.
    Raises ContractViolation if invalid.
    """
    # Check if data is dict
    if not isinstance(data, dict):
        raise ContractViolation("INVALID_REQUEST", "Request must be JSON object")
    
    # Check for forbidden fields
    allowed_fields = {"text", "context"}
    actual_fields = set(data.keys())
    forbidden_fields = actual_fields - allowed_fields
    if forbidden_fields:
        raise ContractViolation("FORBIDDEN_FIELD", f"Forbidden fields: {list(forbidden_fields)}")
    
    # Check for missing required field
    if "text" not in data:
        raise ContractViolation("MISSING_FIELD", "Required field 'text' is missing")
    
    text = data["text"]
    
    # Type enforcement
    if not isinstance(text, str):
        raise ContractViolation("INVALID_TYPE", "Field 'text' must be a string")
        
    # Context enforcement (Misuse Detection)
    if "context" in data:
        context = data["context"]
        if not isinstance(context, dict):
            raise ContractViolation("INVALID_CONTEXT", "Field 'context' must be a JSON object")
            
        # M-01: Reject Enforcement Roles
        if "role" in context:
            forbidden_roles = {"enforcement", "decision_maker", "judge", "execution", "admin"}
            if context["role"].lower() in forbidden_roles:
                raise ContractViolation("FORBIDDEN_ROLE", f"Role '{context['role']}' is strictly prohibited. This system cannot be used by enforcement roles.")
        
        # M-02: Reject Decision Injection
        forbidden_context_fields = {"action", "decision", "execute", "perform_action", "override_risk"}
        actual_context_fields = set(context.keys())
        found_forbidden = actual_context_fields.intersection(forbidden_context_fields)
        if found_forbidden:
            raise ContractViolation("DECISION_INJECTION", f"Forbidden decision fields detected: {list(found_forbidden)}. System cannot execute actions.")

    # Length enforcement (before normalization)
    if len(text) > MAX_TEXT_LENGTH:
        # This is handled by truncation, not rejection
        pass
    
    # Encoding enforcement (UTF-8 validation)
    try:
        text.encode('utf-8')
    except UnicodeEncodeError:
        raise ContractViolation("INVALID_ENCODING", "Text contains invalid UTF-8 sequences")
    
    return text

def validate_output_contract(response: Dict[str, Any]) -> None:
    """
    Validates output against sealed contract.
    Raises ContractViolation if invalid.
    """
    required_fields = {
        "risk_score", "confidence_score", "risk_category", 
        "trigger_reasons", "processed_length", "safety_metadata", "errors"
    }
    
    # Check all required fields present
    actual_fields = set(response.keys())
    missing_fields = required_fields - actual_fields
    if missing_fields:
        raise ContractViolation("MISSING_OUTPUT_FIELD", f"Missing fields: {list(missing_fields)}")
    
    # Check no forbidden fields
    forbidden_fields = actual_fields - required_fields
    if forbidden_fields:
        raise ContractViolation("FORBIDDEN_OUTPUT_FIELD", f"Forbidden fields: {list(forbidden_fields)}")
    
    # Validate risk_score
    risk_score = response["risk_score"]
    if not isinstance(risk_score, (int, float)) or isinstance(risk_score, bool):
        raise ContractViolation("INVALID_RISK_SCORE_TYPE", "risk_score must be number")
    if not (0.0 <= risk_score <= 1.0):
        raise ContractViolation("INVALID_RISK_SCORE_RANGE", "risk_score must be 0.0-1.0")
    
    # Validate confidence_score
    confidence_score = response["confidence_score"]
    if not isinstance(confidence_score, (int, float)) or isinstance(confidence_score, bool):
        raise ContractViolation("INVALID_CONFIDENCE_SCORE_TYPE", "confidence_score must be number")
    if not (0.0 <= confidence_score <= 1.0):
        raise ContractViolation("INVALID_CONFIDENCE_SCORE_RANGE", "confidence_score must be 0.0-1.0")
    
    # Validate risk_category
    risk_category = response["risk_category"]
    if not isinstance(risk_category, str):
        raise ContractViolation("INVALID_RISK_CATEGORY_TYPE", "risk_category must be string")
    if risk_category not in VALID_RISK_CATEGORIES:
        raise ContractViolation("INVALID_RISK_CATEGORY_VALUE", f"risk_category must be one of {VALID_RISK_CATEGORIES}")
    
    # Validate trigger_reasons
    trigger_reasons = response["trigger_reasons"]
    if not isinstance(trigger_reasons, list):
        raise ContractViolation("INVALID_TRIGGER_REASONS_TYPE", "trigger_reasons must be array")
    if len(trigger_reasons) > MAX_TRIGGER_REASONS:
        raise ContractViolation("EXCESSIVE_TRIGGER_REASONS", f"trigger_reasons exceeds max {MAX_TRIGGER_REASONS}")
    for i, reason in enumerate(trigger_reasons):
        if not isinstance(reason, str):
            raise ContractViolation("INVALID_TRIGGER_REASON_TYPE", f"trigger_reasons[{i}] must be string")
    
    # Validate processed_length
    processed_length = response["processed_length"]
    if not isinstance(processed_length, int):
        raise ContractViolation("INVALID_PROCESSED_LENGTH_TYPE", "processed_length must be integer")
    if not (0 <= processed_length <= MAX_TEXT_LENGTH):
        raise ContractViolation("INVALID_PROCESSED_LENGTH_RANGE", f"processed_length must be 0-{MAX_TEXT_LENGTH}")
    
    # Validate safety_metadata (CRITICAL FOR AUTHORITY BOUNDARIES)
    safety_metadata = response["safety_metadata"]
    if not isinstance(safety_metadata, dict):
        raise ContractViolation("INVALID_SAFETY_METADATA_TYPE", "safety_metadata must be object")
    
    required_safety_fields = {"is_decision", "authority", "actionable"}
    actual_safety_fields = set(safety_metadata.keys())
    if actual_safety_fields != required_safety_fields:
        raise ContractViolation("INVALID_SAFETY_METADATA_STRUCTURE", f"safety_metadata must have exactly {required_safety_fields}")
    
    # Enforce non-authority constants
    if safety_metadata["is_decision"] is not False:
        raise ContractViolation("INVALID_IS_DECISION", "is_decision must be False")
    if safety_metadata["authority"] != "NONE":
        raise ContractViolation("INVALID_AUTHORITY", "authority must be 'NONE'")
    if safety_metadata["actionable"] is not False:
        raise ContractViolation("INVALID_ACTIONABLE", "actionable must be False")
    
    # Validate errors
    errors = response["errors"]
    if errors is not None:
        if not isinstance(errors, dict):
            raise ContractViolation("INVALID_ERRORS_TYPE", "errors must be object or null")
        
        required_error_fields = {"error_code", "message"}
        actual_error_fields = set(errors.keys())
        
        if actual_error_fields != required_error_fields:
            raise ContractViolation("INVALID_ERROR_STRUCTURE", f"errors must have exactly {required_error_fields}")
        
        error_code = errors["error_code"]
        if not isinstance(error_code, str):
            raise ContractViolation("INVALID_ERROR_CODE_TYPE", "error_code must be string")
        if error_code not in VALID_ERROR_CODES:
            raise ContractViolation("INVALID_ERROR_CODE_VALUE", f"error_code must be one of {VALID_ERROR_CODES}")
        
        message = errors["message"]
        if not isinstance(message, str):
            raise ContractViolation("INVALID_ERROR_MESSAGE_TYPE", "error message must be string")

def enforce_contracts(func):
    """
    Decorator to enforce input/output contracts on analysis function
    """
    def wrapper(request_data: Any) -> Dict[str, Any]:
        try:
            # Validate input contract
            text = validate_input_contract(request_data)
            
            # Call original function
            response = func(text)
            
            # Validate output contract
            validate_output_contract(response)
            
            return response
            
        except ContractViolation as e:
            # Return contract violation as structured error
            return {
                "risk_score": 0.0,
                "confidence_score": 0.0,
                "risk_category": "LOW",
                "trigger_reasons": [],
                "processed_length": 0,
                "safety_metadata": {
                    "is_decision": False,
                    "authority": "NONE",
                    "actionable": False
                },
                "errors": {
                    "error_code": e.code,
                    "message": e.message
                }
            }
    
    return wrapper