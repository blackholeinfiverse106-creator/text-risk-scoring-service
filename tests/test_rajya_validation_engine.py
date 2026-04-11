"""
Tests for RAJYA — Final Authority Validation Engine
=====================================================
Validates all 4 REJECT paths Rnd the EXECUTION_APPROVED path.

Rules under test (STRICT):
  1. Missing authority (sarathi or enforcement is None) → REJECT
  2. execution_id mismatch → REJECT
  3. Sarathi decision != ALLOW → REJECT
  4. Enforcement decision != ALLOW → REJECT
  Else → EXECUTION_APPROVED
"""

import pytest
from app.rajya_validation_engine import (
    validate_execution_request,
    RajyaValidationResult,
    RajyaRejection,
)


# ============================================================
# Helpers
# ============================================================

def _make_payload(
    execution_id: str = "exec-001",
    sarathi_decision: str | None = "ALLOW",
    sarathi_execution_id: str | None = "exec-001",
    enforcement_verdict: dict | None = None,
) -> dict:
    """Build a valid RAJYA payload. Defaults pass all rules."""
    if enforcement_verdict is None:
        enforcement_verdict = {"enforcement_decision": "ALLOW"}
    return {
        "execution_id": execution_id,
        "sarathi_decision": sarathi_decision,
        "sarathi_execution_id": sarathi_execution_id,
        "enforcement_verdict": enforcement_verdict,
    }


# ============================================================
# EXECUTION_APPROVED — All rules pass
# ============================================================

class TestExecutionApproved:
    def test_all_rules_pass(self):
        """All checks satisfied → EXECUTION_APPROVED."""
        result, rejection = validate_execution_request(_make_payload())
        assert result == RajyaValidationResult.EXECUTION_APPROVED
        assert rejection is None

    def test_approved_with_different_execution_ids(self):
        """Matching but non-trivial execution_ids → APPROVED."""
        payload = _make_payload(
            execution_id="exec-abc123def456",
            sarathi_execution_id="exec-abc123def456",
        )
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.EXECUTION_APPROVED
        assert rejection is None


# ============================================================
# RULE 1 — Missing authority (Sarathi)
# ============================================================

class TestRule1SarathiMissing:
    def test_sarathi_decision_none_rejects(self):
        """Sarathi decision is None → REJECT."""
        payload = _make_payload(sarathi_decision=None)
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection is not None
        assert rejection.code == "RAJYA_SARATHI_AUTHORITY_MISSING"

    def test_sarathi_decision_missing_key_rejects(self):
        """Payload without sarathi_decision key → REJECT."""
        payload = _make_payload()
        del payload["sarathi_decision"]
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_SARATHI_AUTHORITY_MISSING"


# ============================================================
# RULE 1 (cont.) — Missing authority (Enforcement)
# ============================================================

class TestRule1EnforcementMissing:
    def test_enforcement_verdict_none_rejects(self):
        """Enforcement verdict is None → REJECT."""
        payload = _make_payload(enforcement_verdict=None)
        # Manually set to None since helper builds a dict by default
        payload["enforcement_verdict"] = None
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_ENFORCEMENT_AUTHORITY_MISSING"

    def test_enforcement_verdict_not_dict_rejects(self):
        """Enforcement verdict is a string (not dict) → REJECT."""
        payload = _make_payload()
        payload["enforcement_verdict"] = "NOT_A_DICT"
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_ENFORCEMENT_AUTHORITY_MISSING"

    def test_enforcement_verdict_list_rejects(self):
        """Enforcement verdict is a list (not dict) → REJECT."""
        payload = _make_payload()
        payload["enforcement_verdict"] = ["ALLOW"]
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_ENFORCEMENT_AUTHORITY_MISSING"


# ============================================================
# RULE 2 — Execution ID mismatch
# ============================================================

class TestRule2ExecutionIdMismatch:
    def test_mismatched_ids_reject(self):
        """Pipeline exec_id != Sarathi exec_id → REJECT."""
        payload = _make_payload(
            execution_id="exec-AAA",
            sarathi_execution_id="exec-BBB",
        )
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_EXECUTION_ID_MISMATCH"
        assert "exec-AAA" in rejection.reason
        assert "exec-BBB" in rejection.reason

    def test_sarathi_execution_id_none_rejects(self):
        """Sarathi execution_id is None → REJECT (identity can't be verified)."""
        payload = _make_payload(sarathi_execution_id=None)
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_EXECUTION_ID_MISMATCH"


# ============================================================
# RULE 3 — Sarathi decision != ALLOW
# ============================================================

class TestRule3SarathiNotAllow:
    def test_sarathi_deny_rejects(self):
        """Sarathi decision is DENY → REJECT."""
        payload = _make_payload(sarathi_decision="DENY")
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_SARATHI_NOT_ALLOW"
        assert "DENY" in rejection.reason

    def test_sarathi_abstain_rejects(self):
        """Sarathi decision is ABSTAIN → REJECT."""
        payload = _make_payload(sarathi_decision="ABSTAIN")
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_SARATHI_NOT_ALLOW"
        assert "ABSTAIN" in rejection.reason

    def test_sarathi_unknown_value_rejects(self):
        """Sarathi decision is an unexpected value → REJECT."""
        payload = _make_payload(sarathi_decision="MAYBE")
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_SARATHI_NOT_ALLOW"


# ============================================================
# RULE 4 — Enforcement decision != ALLOW
# ============================================================

class TestRule4EnforcementNotAllow:
    def test_enforcement_deny_rejects(self):
        """Enforcement decision is DENY → REJECT."""
        payload = _make_payload(enforcement_verdict={"enforcement_decision": "DENY"})
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_ENFORCEMENT_NOT_ALLOW"

    def test_enforcement_abstain_rejects(self):
        """Enforcement decision is ABSTAIN → REJECT."""
        payload = _make_payload(enforcement_verdict={"enforcement_decision": "ABSTAIN"})
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_ENFORCEMENT_NOT_ALLOW"

    def test_enforcement_decision_none_in_dict_rejects(self):
        """Enforcement verdict dict with enforcement_decision=None → REJECT."""
        payload = _make_payload(enforcement_verdict={"enforcement_decision": None})
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_ENFORCEMENT_NOT_ALLOW"

    def test_enforcement_decision_missing_key_rejects(self):
        """Enforcement verdict dict without enforcement_decision key → REJECT."""
        payload = _make_payload(enforcement_verdict={"some_other_key": "value"})
        result, rejection = validate_execution_request(payload)
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_ENFORCEMENT_NOT_ALLOW"


# ============================================================
# Rule priority — first failing rule wins
# ============================================================

class TestRulePriority:
    def test_sarathi_missing_trumps_enforcement_missing(self):
        """Rule 1 (sarathi missing) fires before Rule 1 (enforcement missing)."""
        payload = {
            "execution_id": "exec-001",
            "sarathi_decision": None,
            "sarathi_execution_id": "exec-001",
            "enforcement_verdict": None,
        }
        result, rejection = validate_execution_request(payload)
        assert rejection.code == "RAJYA_SARATHI_AUTHORITY_MISSING"

    def test_enforcement_missing_trumps_id_mismatch(self):
        """Rule 1 (enforcement missing) fires before Rule 2 (id mismatch)."""
        payload = {
            "execution_id": "exec-AAA",
            "sarathi_decision": "ALLOW",
            "sarathi_execution_id": "exec-BBB",
            "enforcement_verdict": None,
        }
        result, rejection = validate_execution_request(payload)
        assert rejection.code == "RAJYA_ENFORCEMENT_AUTHORITY_MISSING"

    def test_id_mismatch_trumps_sarathi_not_allow(self):
        """Rule 2 (id mismatch) fires before Rule 3 (sarathi != ALLOW)."""
        payload = _make_payload(
            execution_id="exec-AAA",
            sarathi_decision="DENY",
            sarathi_execution_id="exec-BBB",
        )
        result, rejection = validate_execution_request(payload)
        assert rejection.code == "RAJYA_EXECUTION_ID_MISMATCH"


# ============================================================
# RajyaRejection dataclass integrity
# ============================================================

class TestRajyaRejectionDataclass:
    def test_rejection_is_frozen(self):
        """RajyaRejection is immutable (frozen dataclass)."""
        rejection = RajyaRejection(code="TEST", reason="test reason")
        with pytest.raises(AttributeError):
            rejection.code = "MUTATED"

    def test_rejection_fields(self):
        """RajyaRejection has code and reason fields."""
        rejection = RajyaRejection(code="CODE_1", reason="Reason text")
        assert rejection.code == "CODE_1"
        assert rejection.reason == "Reason text"


# ============================================================
# RajyaValidationResult enum integrity
# ============================================================

class TestRajyaValidationResultEnum:
    def test_only_two_values(self):
        """RAJYA can only produce EXECUTION_APPROVED or REJECT."""
        values = {member.value for member in RajyaValidationResult}
        assert values == {"EXECUTION_APPROVED", "REJECT"}

    def test_string_comparison(self):
        """RajyaValidationResult is a string enum for easy logging."""
        assert RajyaValidationResult.EXECUTION_APPROVED == "EXECUTION_APPROVED"
        assert RajyaValidationResult.REJECT == "REJECT"
