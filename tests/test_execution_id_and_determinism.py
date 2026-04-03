"""
Tests for Phase 6 (Execution ID Enforcement) and Phase 7 (Determinism Validation)
===================================================================================

Phase 6: Validates that execution_id flows unchanged through:
  DGIC → Sarathi → Enforcement → Core → Bucket → InsightBridge
  Mismatch → immediate DENY rejection.

Phase 7: Validates determinism — same input produces identical:
  • decision
  • execution_status (executed)
  • trace_hash
  Across 1000 iterations.
"""

import hashlib
import pytest
from unittest.mock import patch, MagicMock

from app.layer4_core import submit_proposal, CoreExecutionResult
from app.layer5_bucket import get_bucket_entries
from app.enforcement_schemas import (
    EvaluateActionRequest,
    SarathiEvaluateResponse,
    SarathiDecision,
    EnforcementDecision,
    ContextSignal,
    DGICEpistemicStateInput,
    SourceSystem,
)
from app.layer1_sarathi import evaluate_action, compute_trace_hash
from app.layer3_dgic import compute_envelope_hash


# ============================================================
# Helpers
# ============================================================

def _make_lineage_hash(seed: str = "determinism-test") -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _make_dgic_state(
    epistemic_state: str = "KNOWN",
    entropy_score: float = 0.1,
    contradiction_flag: bool = False,
    lineage_seed: str = "determinism-lineage",
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


def _make_request(
    execution_id: str = "exec-determinism-001",
    proposed_action: str = "Generate daily report",
    epistemic_state: str = "KNOWN",
    entropy_score: float = 0.1,
) -> EvaluateActionRequest:
    dgic = _make_dgic_state(
        epistemic_state=epistemic_state,
        entropy_score=entropy_score,
    )
    return EvaluateActionRequest(
        execution_id=execution_id,
        actor="determinism-agent",
        proposed_action=proposed_action,
        context_signals=[],
        dgic_epistemic_state=dgic,
        source_system=SourceSystem.AI_BEING,
    )





# ============================================================
# Phase 6: Execution ID Enforcement Tests
# ============================================================

class TestExecutionIdEnforcement:
    """Validates execution_id propagation across all layer boundaries."""

    def test_execution_id_propagates_through_full_pipeline(self):
        """Same execution_id must appear in request, Sarathi response, and Core result."""
        exec_id = "exec-id-propagation-001"
        result = submit_proposal(
            execution_id=exec_id,
            actor="propagation-agent",
            proposed_action="Generate daily report",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        assert result.execution_id == exec_id

    @patch("app.layer4_core.write_execution_record")
    def test_execution_id_in_ledger_matches(self, mock_write):
        """The ledger entry must carry the same execution_id."""
        exec_id = "exec-id-ledger-001"
        submit_proposal(
            execution_id=exec_id,
            actor="ledger-agent",
            proposed_action="Test action",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        mock_write.assert_called_once()
        assert mock_write.call_args[1]["execution_id"] == exec_id

    def test_sarathi_preserves_execution_id(self):
        """Sarathi must return the same execution_id it received."""
        exec_id = "exec-id-sarathi-001"
        request = _make_request(execution_id=exec_id)
        response = evaluate_action(request)
        assert response.execution_id == exec_id

    def test_sarathi_preserves_execution_id_on_deny(self):
        """Execution_id preservation must hold on DENY paths too."""
        exec_id = "exec-id-deny-001"
        request = _make_request(
            execution_id=exec_id,
            proposed_action="kill and murder and bomb attack terrorist assault",
        )
        response = evaluate_action(request)
        assert response.execution_id == exec_id
        assert response.sarathi_decision == SarathiDecision.DENY

    def test_sarathi_preserves_execution_id_on_abstain(self):
        """Execution_id preservation must hold on ABSTAIN paths."""
        exec_id = "exec-id-abstain-001"
        request = _make_request(
            execution_id=exec_id,
            epistemic_state="UNKNOWN",
            entropy_score=0.0,
        )
        response = evaluate_action(request)
        assert response.execution_id == exec_id
        assert response.sarathi_decision == SarathiDecision.ABSTAIN

    def test_execution_id_mismatch_blocks(self):
        """If Sarathi returns a different execution_id, Core must DENY."""
        exec_id = "exec-mismatch-001"

        # Create a mock Sarathi response with a DIFFERENT execution_id
        fake_sarathi_response = SarathiEvaluateResponse(
            execution_id="WRONG-ID-999",  # MISMATCH
            risk_score=0.1,
            sarathi_decision=SarathiDecision.ALLOW,
            confidence=0.9,
            failure_reason=None,
            trace_hash="a" * 64,
        )

        with patch("app.layer4_core.sarathi_evaluate", return_value=fake_sarathi_response):
            result = submit_proposal(
                execution_id=exec_id,
                actor="mismatch-agent",
                proposed_action="Test action",
                context_signals=[],
                dgic_epistemic_state=_make_dgic_state(),
                source_system=SourceSystem.AI_BEING,
            )

        # Must be DENIED due to mismatch
        assert result.enforcement_decision == EnforcementDecision.DENY
        assert "mismatch" in result.failure_reason.lower()
        assert result.execution_id == exec_id  # Must preserve the ORIGINAL id

    def test_trace_hash_deterministic_for_same_execution_id(self):
        """Same execution_id + same inputs → same trace_hash."""
        request = _make_request(execution_id="exec-trace-001")
        hash1 = compute_trace_hash(request)
        hash2 = compute_trace_hash(request)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_different_execution_ids_different_trace_hash(self):
        """Different execution_ids → different trace_hashes."""
        req1 = _make_request(execution_id="exec-diff-001")
        req2 = _make_request(execution_id="exec-diff-002")
        assert compute_trace_hash(req1) != compute_trace_hash(req2)


# ============================================================
# Phase 7: Determinism Validation (1000 iterations)
# ============================================================

class TestDeterminismValidation:
    """
    Validates that the enforcement pipeline is fully deterministic.
    Same input → same decision, same execution_status, same trace_hash.
    Minimum 1000 iterations.
    """

    def test_allow_determinism_1000_iterations(self):
        """ALLOW path: 1000 iterations must produce identical results."""
        request = _make_request(
            execution_id="det-allow-001",
            proposed_action="Generate daily report",
        )

        # Get the reference result
        ref = evaluate_action(request)
        ref_decision = ref.sarathi_decision.value
        ref_risk = ref.risk_score
        ref_confidence = ref.confidence
        ref_hash = ref.trace_hash
        ref_reason = ref.failure_reason

        assert ref_decision == "ALLOW"

        # Run 1000 iterations
        for i in range(1000):
            result = evaluate_action(request)
            assert result.sarathi_decision.value == ref_decision, \
                f"Decision diverged at iteration {i}: expected {ref_decision}, got {result.sarathi_decision.value}"
            assert result.risk_score == ref_risk, \
                f"Risk score diverged at iteration {i}: expected {ref_risk}, got {result.risk_score}"
            assert result.confidence == ref_confidence, \
                f"Confidence diverged at iteration {i}: expected {ref_confidence}, got {result.confidence}"
            assert result.trace_hash == ref_hash, \
                f"Trace hash diverged at iteration {i}: expected {ref_hash}, got {result.trace_hash}"
            assert result.failure_reason == ref_reason, \
                f"Failure reason diverged at iteration {i}"

    def test_deny_determinism_1000_iterations(self):
        """DENY path: 1000 iterations must produce identical results."""
        request = _make_request(
            execution_id="det-deny-001",
            proposed_action="kill murder bomb terrorist attack shoot explode",
        )

        ref = evaluate_action(request)
        ref_decision = ref.sarathi_decision.value
        ref_risk = ref.risk_score
        ref_hash = ref.trace_hash

        assert ref_decision == "DENY"

        for i in range(1000):
            result = evaluate_action(request)
            assert result.sarathi_decision.value == ref_decision, \
                f"Decision diverged at iteration {i}"
            assert result.risk_score == ref_risk, \
                f"Risk score diverged at iteration {i}"
            assert result.trace_hash == ref_hash, \
                f"Trace hash diverged at iteration {i}"

    def test_abstain_determinism_1000_iterations(self):
        """ABSTAIN path: 1000 iterations must produce identical results."""
        request = _make_request(
            execution_id="det-abstain-001",
            epistemic_state="UNKNOWN",
            entropy_score=0.0,
        )

        ref = evaluate_action(request)
        ref_decision = ref.sarathi_decision.value
        ref_risk = ref.risk_score
        ref_hash = ref.trace_hash

        assert ref_decision == "ABSTAIN"

        for i in range(1000):
            result = evaluate_action(request)
            assert result.sarathi_decision.value == ref_decision, \
                f"Decision diverged at iteration {i}"
            assert result.risk_score == ref_risk, \
                f"Risk score diverged at iteration {i}"
            assert result.trace_hash == ref_hash, \
                f"Trace hash diverged at iteration {i}"

    @patch("app.layer5_bucket.requests.post")
    def test_full_pipeline_determinism_1000_iterations(self, mock_post):
        """Full Core pipeline: 1000 iterations must produce identical CoreExecutionResult."""
        # Mock bucket POST to avoid 1000 HTTP calls
        mock_post.return_value = MagicMock()
        mock_post.return_value.raise_for_status = MagicMock()

        dgic = _make_dgic_state()

        # Get reference result
        ref = submit_proposal(
            execution_id="det-full-001",
            actor="determinism-agent",
            proposed_action="Generate daily report",
            context_signals=[],
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.AI_BEING,
        )

        ref_decision = ref.enforcement_decision.value
        ref_risk = ref.risk_score
        ref_hash = ref.trace_hash

        for i in range(1000):
            result = submit_proposal(
                execution_id="det-full-001",
                actor="determinism-agent",
                proposed_action="Generate daily report",
                context_signals=[],
                dgic_epistemic_state=dgic,
                source_system=SourceSystem.AI_BEING,
            )
            assert result.enforcement_decision.value == ref_decision, \
                f"enforcement_decision diverged at iteration {i}"
            assert result.risk_score == ref_risk, \
                f"risk_score diverged at iteration {i}"
            assert result.trace_hash == ref_hash, \
                f"trace_hash diverged at iteration {i}"

    def test_context_signal_determinism_1000_iterations(self):
        """With context signals: 1000 iterations must produce identical results."""
        signals = [
            ContextSignal(signal_id="sig-1", signal_type="security_alert", value=0.5, source="INSIGHTBRIDGE"),
            ContextSignal(signal_id="sig-2", signal_type="anomaly", value=0.3, source="MARINE_INTELLIGENCE"),
        ]
        dgic = _make_dgic_state()

        request = EvaluateActionRequest(
            execution_id="det-signals-001",
            actor="signal-agent",
            proposed_action="Execute trade operation",
            context_signals=signals,
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.SOVEREIGN_CORE,
        )

        ref = evaluate_action(request)

        for i in range(1000):
            result = evaluate_action(request)
            assert result.sarathi_decision == ref.sarathi_decision, \
                f"Decision diverged at iteration {i}"
            assert result.risk_score == ref.risk_score, \
                f"Risk score diverged at iteration {i}"
            assert result.trace_hash == ref.trace_hash, \
                f"Trace hash diverged at iteration {i}"
            assert result.confidence == ref.confidence, \
                f"Confidence diverged at iteration {i}"
