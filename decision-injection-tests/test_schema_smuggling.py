"""
decision-injection-tests/test_schema_smuggling.py
==================================================
Penetration tests: type coercion and schema smuggling attacks.
Attempts to bypass string validation via type abuse, extra fields,
and unusual payload shapes.

All tests verify the contract layer rejects the attack with the
appropriate error code.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.contract_enforcement import validate_input_contract, ContractViolation


# ── Type coercion attacks ────────────────────────────────────────────────────

def test_integer_as_text():
    """text=12345 (integer) must be rejected with INVALID_TYPE."""
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": 12345})
    assert exc.value.code == "INVALID_TYPE"


def test_boolean_true_as_text():
    """text=True (boolean) must be rejected with INVALID_TYPE."""
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": True})
    assert exc.value.code == "INVALID_TYPE"


def test_boolean_false_as_text():
    """text=False (boolean) must be rejected with INVALID_TYPE."""
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": False})
    assert exc.value.code == "INVALID_TYPE"


def test_list_as_text():
    """text=['kill'] (list) must be rejected with INVALID_TYPE."""
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": ["kill", "attack"]})
    assert exc.value.code == "INVALID_TYPE"


def test_dict_as_text():
    """text={...} (dict) must be rejected with INVALID_TYPE."""
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": {"content": "kill"}})
    assert exc.value.code == "INVALID_TYPE"


def test_null_as_text():
    """text=None (null) must be rejected with INVALID_TYPE."""
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": None})
    assert exc.value.code == "INVALID_TYPE"


def test_float_as_text():
    """text=3.14 (float) must be rejected with INVALID_TYPE."""
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": 3.14})
    assert exc.value.code == "INVALID_TYPE"


# ── Extra field smuggling ────────────────────────────────────────────────────

def test_extra_top_level_field_score():
    """Extra field 'score' at top level must be rejected with FORBIDDEN_FIELD."""
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": "hello", "score": 0.9})
    assert exc.value.code == "FORBIDDEN_FIELD"


def test_extra_top_level_field_verdict():
    """Extra field 'verdict' at top level must be rejected with FORBIDDEN_FIELD."""
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": "hello", "verdict": "guilty"})
    assert exc.value.code == "FORBIDDEN_FIELD"


def test_missing_text_field():
    """Payload with no 'text' field must be rejected with MISSING_FIELD."""
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"context": {"role": "user"}})
    assert exc.value.code == "MISSING_FIELD"


def test_non_dict_context():
    """context as a string (not dict) must be rejected with INVALID_CONTEXT."""
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": "hello", "context": "admin"})
    assert exc.value.code == "INVALID_CONTEXT"


def test_non_dict_context_list():
    """context as a list must be rejected with INVALID_CONTEXT."""
    with pytest.raises(ContractViolation) as exc:
        validate_input_contract({"text": "hello", "context": ["admin"]})
    assert exc.value.code == "INVALID_CONTEXT"


def test_entirely_non_dict_payload():
    """A non-dict payload (e.g. bare string) must be rejected."""
    with pytest.raises(ContractViolation):
        validate_input_contract("kill attack")


def test_entirely_non_dict_payload_list():
    """A list payload must be rejected."""
    with pytest.raises(ContractViolation):
        validate_input_contract(["text", "kill"])
