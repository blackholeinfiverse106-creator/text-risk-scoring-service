"""
escalation-tests/test_output_mutation.py
========================================
Proves that ALL 6 authority field mutations in safety_metadata are
caught by validate_output_contract() and raise ContractViolation.

This closes the output-side of the authority containment proof:
even if an attacker gained code execution and mutated the dict,
the contract validator would block propagation.
"""
import pytest
import copy
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.engine import analyze_text
from app.contract_enforcement import validate_output_contract, ContractViolation


@pytest.fixture
def valid_high_risk_output():
    """A real HIGH-risk output that passes contract validation."""
    result = analyze_text("kill murder attack bomb terrorist")
    assert result["risk_category"] == "HIGH"
    validate_output_contract(result)   # baseline: must pass
    return result


# ── is_decision mutations ────────────────────────────────────────────────────

def test_mutation_is_decision_true(valid_high_risk_output):
    """is_decision=True must be rejected with INVALID_IS_DECISION."""
    mutated = copy.deepcopy(valid_high_risk_output)
    mutated["safety_metadata"]["is_decision"] = True
    with pytest.raises(ContractViolation) as exc:
        validate_output_contract(mutated)
    assert exc.value.code == "INVALID_IS_DECISION"


def test_mutation_is_decision_string(valid_high_risk_output):
    """is_decision='true' (string) must be rejected."""
    mutated = copy.deepcopy(valid_high_risk_output)
    mutated["safety_metadata"]["is_decision"] = "true"
    with pytest.raises(ContractViolation) as exc:
        validate_output_contract(mutated)
    assert exc.value.code == "INVALID_IS_DECISION"


def test_mutation_is_decision_one(valid_high_risk_output):
    """is_decision=1 (truthy int) must be rejected."""
    mutated = copy.deepcopy(valid_high_risk_output)
    mutated["safety_metadata"]["is_decision"] = 1
    with pytest.raises(ContractViolation) as exc:
        validate_output_contract(mutated)
    assert exc.value.code == "INVALID_IS_DECISION"


# ── authority mutations ───────────────────────────────────────────────────────

def test_mutation_authority_full(valid_high_risk_output):
    """authority='FULL' must be rejected with INVALID_AUTHORITY."""
    mutated = copy.deepcopy(valid_high_risk_output)
    mutated["safety_metadata"]["authority"] = "FULL"
    with pytest.raises(ContractViolation) as exc:
        validate_output_contract(mutated)
    assert exc.value.code == "INVALID_AUTHORITY"


def test_mutation_authority_admin(valid_high_risk_output):
    """authority='ADMIN' must be rejected."""
    mutated = copy.deepcopy(valid_high_risk_output)
    mutated["safety_metadata"]["authority"] = "ADMIN"
    with pytest.raises(ContractViolation) as exc:
        validate_output_contract(mutated)
    assert exc.value.code == "INVALID_AUTHORITY"


def test_mutation_authority_empty_string(valid_high_risk_output):
    """authority='' (empty string, not 'NONE') must be rejected."""
    mutated = copy.deepcopy(valid_high_risk_output)
    mutated["safety_metadata"]["authority"] = ""
    with pytest.raises(ContractViolation) as exc:
        validate_output_contract(mutated)
    assert exc.value.code == "INVALID_AUTHORITY"


# ── actionable mutations ─────────────────────────────────────────────────────

def test_mutation_actionable_true(valid_high_risk_output):
    """actionable=True must be rejected with INVALID_ACTIONABLE."""
    mutated = copy.deepcopy(valid_high_risk_output)
    mutated["safety_metadata"]["actionable"] = True
    with pytest.raises(ContractViolation) as exc:
        validate_output_contract(mutated)
    assert exc.value.code == "INVALID_ACTIONABLE"


def test_mutation_actionable_string(valid_high_risk_output):
    """actionable='yes' must be rejected."""
    mutated = copy.deepcopy(valid_high_risk_output)
    mutated["safety_metadata"]["actionable"] = "yes"
    with pytest.raises(ContractViolation) as exc:
        validate_output_contract(mutated)
    assert exc.value.code == "INVALID_ACTIONABLE"


# ── Structural mutations ─────────────────────────────────────────────────────

def test_mutation_extra_output_field(valid_high_risk_output):
    """Adding extra output field 'action' must be rejected with FORBIDDEN_OUTPUT_FIELD."""
    mutated = copy.deepcopy(valid_high_risk_output)
    mutated["action"] = "ban"
    with pytest.raises(ContractViolation) as exc:
        validate_output_contract(mutated)
    assert exc.value.code == "FORBIDDEN_OUTPUT_FIELD"


def test_mutation_risk_score_out_of_range(valid_high_risk_output):
    """risk_score=1.5 (out of range) must be rejected."""
    mutated = copy.deepcopy(valid_high_risk_output)
    mutated["risk_score"] = 1.5
    with pytest.raises(ContractViolation) as exc:
        validate_output_contract(mutated)
    assert exc.value.code == "INVALID_RISK_SCORE_RANGE"


def test_valid_output_passes_baseline(valid_high_risk_output):
    """Sanity check: the unmodified HIGH-risk output passes contract validation."""
    # Should not raise
    validate_output_contract(valid_high_risk_output)
