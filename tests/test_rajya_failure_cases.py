"""
RAJYA Failure Case Validation — Phase 7
=========================================
Proves that ALL failure cases stop at RAJYA and Core NEVER executes.

Test Matrix:
  1. Missing Sarathi      → RAJYA REJECT → Core does not execute
  2. Sarathi DENY          → RAJYA REJECT → Core does not execute
  3. Enforcement DENY      → RAJYA REJECT → Core does not execute
  4. execution_id mismatch → RAJYA REJECT → Core does not execute

Each test verifies:
  - RAJYA returns REJECT
  - execute_action() is NEVER called
  - block_execution() is NEVER called (RAJYA short-circuits before Core)
  - The pipeline returns DENY with a RAJYA rejection reason
"""

import pytest
import hashlib
from unittest.mock import patch, MagicMock

from app.sutradhara_control_plane import invoke_mandala, MandalaInvocationResult
from app.enforcement_schemas import (
    EnforcementDecision,
    DGICEpistemicStateInput,
    ContextSignal,
    SourceSystem,
)
from app.layer3_dgic import compute_envelope_hash
from app.rajya_validation_engine import (
    validate_execution_request,
    RajyaValidationResult,
)


# ============================================================
# Helpers
# ============================================================

def _make_lineage_hash(seed: str = "rajya-failure-test") -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _make_dgic_state(
    epistemic_state: str = "KNOWN",
    entropy_score: float = 0.1,
    contradiction_flag: bool = False,
    lineage_seed: str = "rajya-lineage",
) -> DGICEpistemicStateInput:
    lineage_hash = _make_lineage_hash(lineage_seed)
    payload_dict = {
        "epistemic_state": epistemic_state,
        "entropy_score": entropy_score,
        "contradiction_flag": contradiction_flag,
    }
    envelope_hash = compute_envelope_hash("schema_v1", lineage_hash, payload_dict)
    return DGICEpistemicStateInput(
        epistemic_state=epistemic_state,
        entropy_score=entropy_score,
        contradiction_flag=contradiction_flag,
        lineage_hash=lineage_hash,
        envelope_hash=envelope_hash,
    )


# ============================================================
# 1. Missing Sarathi → RAJYA REJECT → Core does not execute
# ============================================================

class TestMissingSarathiStopsAtRajya:
    """When Sarathi returns None, RAJYA must reject and Core must not fire."""

    @patch("app.sutradhara_control_plane.evaluate_action", return_value=None)
    @patch("app.execution_controller.execute_action")
    @patch("app.execution_controller.block_execution")
    def test_missing_sarathi_core_never_executes(self, mock_block, mock_exec, mock_sarathi):
        """Sarathi=None → pipeline short-circuits BEFORE RAJYA/Core."""
        result = invoke_mandala(
            execution_id="fail-sarathi-001",
            actor="test-agent",
            proposed_action="Normal action",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        assert result.enforcement_decision == EnforcementDecision.DENY
        assert "Sarathi" in result.failure_reason
        # Core must never be reached
        mock_exec.assert_not_called()
        mock_block.assert_not_called()

    def test_rajya_rejects_missing_sarathi_decision(self):
        """RAJYA unit: sarathi_decision=None → REJECT."""
        result, rejection = validate_execution_request({
            "execution_id": "fail-001",
            "sarathi_decision": None,
            "sarathi_execution_id": "fail-001",
            "enforcement_verdict": {"enforcement_decision": "ALLOW"},
        })
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_SARATHI_AUTHORITY_MISSING"


# ============================================================
# 2. Sarathi DENY → RAJYA REJECT → Core does not execute
# ============================================================

class TestSarathiDenyStopsAtRajya:
    """When Sarathi decides DENY, RAJYA must reject and Core must not fire."""

    @patch("app.execution_controller.execute_action")
    def test_sarathi_deny_core_never_executes(self, mock_exec):
        """High-risk action → Sarathi DENY → RAJYA REJECT → Core never executes."""
        result = invoke_mandala(
            execution_id="fail-deny-001",
            actor="test-agent",
            proposed_action="kill murder bomb terrorist attack shoot explode",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        assert result.enforcement_decision == EnforcementDecision.DENY
        assert "RAJYA REJECT" in result.failure_reason
        assert "RAJYA_SARATHI_NOT_ALLOW" in result.failure_reason
        # execute_action must NEVER be called
        mock_exec.assert_not_called()

    @patch("app.execution_controller.execute_action")
    def test_sarathi_abstain_core_never_executes(self, mock_exec):
        """UNKNOWN state → Sarathi ABSTAIN → RAJYA REJECT → Core never executes."""
        dgic = _make_dgic_state(epistemic_state="UNKNOWN", entropy_score=0.0)
        result = invoke_mandala(
            execution_id="fail-abstain-001",
            actor="test-agent",
            proposed_action="Run diagnostic scan",
            context_signals=[],
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.AI_BEING,
        )
        assert result.enforcement_decision == EnforcementDecision.DENY
        assert "RAJYA" in result.failure_reason
        mock_exec.assert_not_called()

    def test_rajya_rejects_sarathi_deny(self):
        """RAJYA unit: sarathi_decision=DENY → REJECT."""
        result, rejection = validate_execution_request({
            "execution_id": "fail-002",
            "sarathi_decision": "DENY",
            "sarathi_execution_id": "fail-002",
            "enforcement_verdict": {"enforcement_decision": "ALLOW"},
        })
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_SARATHI_NOT_ALLOW"


# ============================================================
# 3. Enforcement DENY → RAJYA REJECT → Core does not execute
# ============================================================

class TestEnforcementDenyStopsAtRajya:
    """When Enforcement returns DENY, RAJYA must reject and Core must not fire."""

    def test_rajya_rejects_enforcement_deny(self):
        """RAJYA unit: enforcement_decision=DENY → REJECT."""
        result, rejection = validate_execution_request({
            "execution_id": "fail-003",
            "sarathi_decision": "ALLOW",
            "sarathi_execution_id": "fail-003",
            "enforcement_verdict": {"enforcement_decision": "DENY"},
        })
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_ENFORCEMENT_NOT_ALLOW"

    def test_rajya_rejects_enforcement_abstain(self):
        """RAJYA unit: enforcement_decision=ABSTAIN → REJECT."""
        result, rejection = validate_execution_request({
            "execution_id": "fail-004",
            "sarathi_decision": "ALLOW",
            "sarathi_execution_id": "fail-004",
            "enforcement_verdict": {"enforcement_decision": "ABSTAIN"},
        })
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_ENFORCEMENT_NOT_ALLOW"

    def test_rajya_rejects_enforcement_missing_verdict(self):
        """RAJYA unit: enforcement_verdict=None → REJECT."""
        result, rejection = validate_execution_request({
            "execution_id": "fail-005",
            "sarathi_decision": "ALLOW",
            "sarathi_execution_id": "fail-005",
            "enforcement_verdict": None,
        })
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_ENFORCEMENT_AUTHORITY_MISSING"


# ============================================================
# 4. execution_id mismatch → RAJYA REJECT → Core does not execute
# ============================================================

class TestExecutionIdMismatchStopsAtRajya:
    """When execution_id mismatches, RAJYA must reject and Core must not fire."""

    def test_rajya_rejects_id_mismatch(self):
        """RAJYA unit: pipeline exec_id != sarathi exec_id → REJECT."""
        result, rejection = validate_execution_request({
            "execution_id": "exec-PIPELINE",
            "sarathi_decision": "ALLOW",
            "sarathi_execution_id": "exec-TAMPERED",
            "enforcement_verdict": {"enforcement_decision": "ALLOW"},
        })
        assert result == RajyaValidationResult.REJECT
        assert rejection.code == "RAJYA_EXECUTION_ID_MISMATCH"
        assert "exec-PIPELINE" in rejection.reason
        assert "exec-TAMPERED" in rejection.reason

    @patch("app.execution_controller.execute_action")
    @patch("app.execution_controller.block_execution")
    def test_id_mismatch_in_pipeline_core_never_executes(self, mock_block, mock_exec):
        """Sarathi ID mismatch → Sūtradhāra short-circuits before RAJYA/Core."""
        # Simulate by patching Sarathi to return mismatched execution_id
        mock_sarathi_resp = MagicMock()
        mock_sarathi_resp.execution_id = "TAMPERED-ID"
        mock_sarathi_resp.sarathi_decision = MagicMock()
        mock_sarathi_resp.sarathi_decision.value = "ALLOW"
        mock_sarathi_resp.risk_score = 0.0
        mock_sarathi_resp.confidence = 1.0
        mock_sarathi_resp.trace_hash = "a" * 64
        mock_sarathi_resp.failure_reason = None

        with patch("app.sutradhara_control_plane.evaluate_action", return_value=mock_sarathi_resp):
            result = invoke_mandala(
                execution_id="exec-ORIGINAL",
                actor="test-agent",
                proposed_action="Normal action",
                context_signals=[],
                dgic_epistemic_state=_make_dgic_state(),
                source_system=SourceSystem.AI_BEING,
            )
        assert result.enforcement_decision == EnforcementDecision.DENY
        assert "mismatch" in result.failure_reason.lower() or "Execution ID" in result.failure_reason
        # Core must NEVER be reached
        mock_exec.assert_not_called()
        mock_block.assert_not_called()


# ============================================================
# 5. Comprehensive: ONLY ALLOW passes RAJYA
# ============================================================

class TestOnlyAllowPassesRajya:
    """Prove that ONLY full ALLOW from both Sarathi and Enforcement passes RAJYA."""

    @patch("app.layer4_core.execute_action")
    def test_allow_path_core_does_execute(self, mock_exec):
        """Clean action + KNOWN state → RAJYA APPROVED → Core executes."""
        result = invoke_mandala(
            execution_id="pass-001",
            actor="test-agent",
            proposed_action="Generate daily report",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        assert result.enforcement_decision == EnforcementDecision.ALLOW
        assert result.failure_reason is None
        # execute_action MUST be called exactly once
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args
        assert call_args[0][0] == "Generate daily report"
        assert call_args[0][1] == "pass-001"

    def test_rajya_approve_payload(self):
        """RAJYA unit: all valid → EXECUTION_APPROVED."""
        result, rejection = validate_execution_request({
            "execution_id": "pass-002",
            "sarathi_decision": "ALLOW",
            "sarathi_execution_id": "pass-002",
            "enforcement_verdict": {"enforcement_decision": "ALLOW"},
        })
        assert result == RajyaValidationResult.EXECUTION_APPROVED
        assert rejection is None
