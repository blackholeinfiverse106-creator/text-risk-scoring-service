"""
escalation-tests/test_escalation_chains.py
==========================================
Multi-step authority escalation simulation.

Proves that each step in an escalation chain is independently blocked —
there is no "trust building" that accumulates across requests.

Step model:
  Step 1: Legitimate request (base case — succeeds)
  Step 2: Role injection (blocked: FORBIDDEN_ROLE)
  Step 3: Decision injection (blocked: DECISION_INJECTION)
  Step 4: Score-as-mandate (blocked: no action field in output)
  Step 5: Output mutation (blocked: ContractViolation at output layer)
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.engine import analyze_text
from app.contract_enforcement import (
    validate_input_contract, validate_output_contract, ContractViolation
)


class TestEscalationChainAdmin:
    """Full 5-step admin role escalation chain."""

    def test_step1_legitimate_request(self):
        """Step 1: Legitimate request succeeds."""
        result = analyze_text("this is a normal message")
        assert result["safety_metadata"]["authority"] == "NONE"
        assert result["safety_metadata"]["is_decision"] is False

    def test_step2_role_injection_blocked(self):
        """Step 2: Attacker injects admin role — must be blocked."""
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": "normal message", "context": {"role": "admin"}})
        assert exc.value.code == "FORBIDDEN_ROLE"

    def test_step3_decision_injection_blocked(self):
        """Step 3: Attacker injects action field — must be blocked."""
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": "normal message", "context": {"action": "grant_admin"}})
        assert exc.value.code == "DECISION_INJECTION"

    def test_step4_high_score_is_not_a_mandate(self):
        """Step 4: Attacker uses HIGH risk score as enforcement mandate.
        Proves: HIGH output has no 'action', 'execute', or 'command' fields.
        """
        result = analyze_text("kill murder attack bomb terrorist")
        assert result["risk_category"] == "HIGH"
        # No action fields exist in the response
        for field in ("action", "execute", "command", "ban", "block", "delete"):
            assert field not in result, f"Forbidden field '{field}' found in output"
        # is_decision is still False at HIGH
        assert result["safety_metadata"]["is_decision"] is False

    def test_step5_output_mutation_blocked(self):
        """Step 5: Attacker mutates output to claim authority.
        validate_output_contract must reject the mutation.
        """
        result = analyze_text("kill attack")
        # Simulate attacker mutating the output
        result["safety_metadata"]["is_decision"] = True  # ILLEGAL
        with pytest.raises(ContractViolation) as exc:
            validate_output_contract(result)
        assert exc.value.code == "INVALID_IS_DECISION"


class TestEscalationChainJudge:
    """Full 5-step judge role escalation chain."""

    def test_step1_legitimate_request(self):
        result = analyze_text("this content concerns me")
        assert result["safety_metadata"]["authority"] == "NONE"

    def test_step2_judge_role_blocked(self):
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": "content", "context": {"role": "judge"}})
        assert exc.value.code == "FORBIDDEN_ROLE"

    def test_step3_execute_injection_blocked(self):
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": "content", "context": {"execute": "impose_penalty"}})
        assert exc.value.code == "DECISION_INJECTION"

    def test_step4_high_confidence_not_a_verdict(self):
        """High confidence does not constitute a verdict."""
        result = analyze_text("kill murder attack bomb terrorist")
        assert result["confidence_score"] >= 0.8
        # Still not a decision
        assert result["safety_metadata"]["is_decision"] is False
        assert result["safety_metadata"]["actionable"] is False

    def test_step5_authority_mutation_blocked(self):
        result = analyze_text("kill attack murder")
        result["safety_metadata"]["authority"] = "FULL"  # ILLEGAL
        with pytest.raises(ContractViolation) as exc:
            validate_output_contract(result)
        assert exc.value.code == "INVALID_AUTHORITY"


class TestEscalationChainDecisionMaker:
    """Escalation via decision_maker role."""

    def test_decision_maker_role_blocked(self):
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": "text", "context": {"role": "decision_maker"}})
        assert exc.value.code == "FORBIDDEN_ROLE"

    def test_override_risk_blocked(self):
        """Attacker tries to pre-determine score via override_risk."""
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": "kill bomb", "context": {"override_risk": 0.0}})
        assert exc.value.code == "DECISION_INJECTION"

    def test_perform_action_blocked(self):
        """Attacker injects perform_action field."""
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({"text": "text", "context": {"perform_action": "approve_all"}})
        assert exc.value.code == "DECISION_INJECTION"


class TestStatelessnessPreventsTrustBuilding:
    """Prove that prior legitimate requests grant no trust to later requests."""

    def test_10_legitimate_then_escalation_still_blocked(self):
        """10 valid requests establish no trust. The 11th with admin role is still blocked."""
        for _ in range(10):
            result = analyze_text("safe normal content")
            assert result["safety_metadata"]["authority"] == "NONE"

        # 11th request: escalation attempt — still blocked
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({
                "text": "safe normal content",
                "context": {"role": "admin"}
            })
        assert exc.value.code == "FORBIDDEN_ROLE"

    def test_correlation_ids_do_not_accumulate_trust(self):
        """Using different correlation_ids on each request grants no special trust."""
        import uuid
        for i in range(5):
            cid = str(uuid.uuid4())
            result = analyze_text("normal content", correlation_id=cid)
            assert result["safety_metadata"]["is_decision"] is False

        # Now try to escalate using a real correlation_id
        with pytest.raises(ContractViolation) as exc:
            validate_input_contract({
                "text": "normal content",
                "context": {"role": "enforcement"}
            })
        assert exc.value.code == "FORBIDDEN_ROLE"
