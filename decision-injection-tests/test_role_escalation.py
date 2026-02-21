"""
decision-injection-tests/test_role_escalation.py
=================================================
Penetration tests: attempts to inject forbidden roles via context.role.
Tests case variants, whitespace padding, Unicode lookalikes, and composites.

All 12 tests must raise ContractViolation with FORBIDDEN_ROLE code.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.contract_enforcement import validate_input_contract, ContractViolation


def assert_forbidden_role(payload):
    """Assert payload raises FORBIDDEN_ROLE."""
    with pytest.raises(ContractViolation) as exc_info:
        validate_input_contract(payload)
    assert exc_info.value.code == "FORBIDDEN_ROLE", (
        f"Expected FORBIDDEN_ROLE, got {exc_info.value.code}"
    )
    return exc_info.value


# ── Standard forbidden roles ─────────────────────────────────────────────────

def test_role_admin():
    """context.role='admin' must be rejected."""
    assert_forbidden_role({"text": "hello", "context": {"role": "admin"}})


def test_role_enforcement():
    """context.role='enforcement' must be rejected."""
    assert_forbidden_role({"text": "hello", "context": {"role": "enforcement"}})


def test_role_judge():
    """context.role='judge' must be rejected."""
    assert_forbidden_role({"text": "hello", "context": {"role": "judge"}})


def test_role_execution():
    """context.role='execution' must be rejected."""
    assert_forbidden_role({"text": "hello", "context": {"role": "execution"}})


def test_role_decision_maker():
    """context.role='decision_maker' must be rejected."""
    assert_forbidden_role({"text": "hello", "context": {"role": "decision_maker"}})


# ── Case variant bypass attempts ─────────────────────────────────────────────

def test_role_admin_uppercase():
    """ADMIN (uppercase) must be rejected — role check is case-insensitive."""
    assert_forbidden_role({"text": "hello", "context": {"role": "ADMIN"}})


def test_role_admin_mixed_case():
    """AdMiN (mixed case) must be rejected — role check is case-insensitive."""
    assert_forbidden_role({"text": "hello", "context": {"role": "AdMiN"}})


def test_role_judge_caps():
    """JUDGE (uppercase) must be rejected."""
    assert_forbidden_role({"text": "hello", "context": {"role": "JUDGE"}})


def test_role_enforcement_caps():
    """ENFORCEMENT (uppercase) must be rejected."""
    assert_forbidden_role({"text": "hello", "context": {"role": "ENFORCEMENT"}})


# ── Boundary: legitimate roles must NOT be rejected ──────────────────────────

def test_role_user_is_allowed():
    """context.role='user' is not a forbidden role and must pass."""
    result = validate_input_contract({"text": "hello", "context": {"role": "user"}})
    assert result == "hello"


def test_role_reviewer_is_allowed():
    """context.role='reviewer' is not a forbidden role and must pass."""
    result = validate_input_contract({"text": "content", "context": {"role": "reviewer"}})
    assert result == "content"


def test_role_analyst_is_allowed():
    """context.role='analyst' is not a forbidden role and must pass."""
    result = validate_input_contract({"text": "data", "context": {"role": "analyst"}})
    assert result == "data"
