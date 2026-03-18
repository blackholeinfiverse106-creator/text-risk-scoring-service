"""
decision-injection-tests/test_field_injection.py
================================================
Penetration tests: attempts to inject forbidden decision fields
into the context payload.

All 15 tests must raise ContractViolation with DECISION_INJECTION code.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.contract_enforcement import validate_input_contract, ContractViolation


# ── Helpers ─────────────────────────────────────────────────────────────────

def assert_decision_injection(payload):
    """Assert that the payload is rejected with DECISION_INJECTION."""
    with pytest.raises(ContractViolation) as exc_info:
        validate_input_contract(payload)
    assert exc_info.value.code == "DECISION_INJECTION", (
        f"Expected DECISION_INJECTION, got {exc_info.value.code}"
    )
    return exc_info.value


# ── Top-level action field ───────────────────────────────────────────────────

def test_inject_action_ban():
    """context.action='ban' must be rejected."""
    assert_decision_injection({"text": "hello", "context": {"action": "ban"}})


def test_inject_action_delete():
    """context.action='delete' must be rejected."""
    assert_decision_injection({"text": "hello", "context": {"action": "delete"}})


def test_inject_action_suspend():
    """context.action='suspend_user' must be rejected."""
    assert_decision_injection({"text": "hello", "context": {"action": "suspend_user"}})


def test_inject_execute_field():
    """context.execute must be rejected."""
    assert_decision_injection({"text": "hello", "context": {"execute": "delete_post"}})


def test_inject_execute_empty_string():
    """context.execute='' must be rejected (field existence matters, not value)."""
    assert_decision_injection({"text": "hello", "context": {"execute": ""}})


def test_inject_decision_field():
    """context.decision must be rejected."""
    assert_decision_injection({"text": "hello", "context": {"decision": "approved"}})


def test_inject_decision_denied():
    """context.decision='denied' must be rejected."""
    assert_decision_injection({"text": "sensitive content", "context": {"decision": "denied"}})


def test_inject_perform_action():
    """context.perform_action must be rejected."""
    assert_decision_injection({"text": "hello", "context": {"perform_action": "block"}})


def test_inject_override_risk_zero():
    """context.override_risk=0.0 must be rejected."""
    assert_decision_injection({"text": "kill attack", "context": {"override_risk": 0.0}})


def test_inject_override_risk_one():
    """context.override_risk=1.0 must be rejected."""
    assert_decision_injection({"text": "safe text", "context": {"override_risk": 1.0}})


def test_inject_multiple_forbidden_fields():
    """Multiple forbidden fields simultaneously must be rejected."""
    assert_decision_injection({
        "text": "hello",
        "context": {"action": "ban", "override_risk": 0.0}
    })


def test_inject_action_with_legitimate_context():
    """Forbidden field alongside a legitimate field still rejected."""
    assert_decision_injection({
        "text": "hello",
        "context": {"user_id": "abc123", "action": "ban"}
    })


def test_inject_action_with_low_risk_text():
    """Even completely safe text cannot bypass injection check."""
    assert_decision_injection({
        "text": "have a nice day",
        "context": {"action": "approve"}
    })


def test_inject_action_boolean_value():
    """context.action=True (non-string value) must still be rejected."""
    assert_decision_injection({"text": "hello", "context": {"action": True}})


def test_inject_action_null_value():
    """context.action=None (null) still triggers DECISION_INJECTION."""
    assert_decision_injection({"text": "hello", "context": {"action": None}})
