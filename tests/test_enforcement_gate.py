"""
Tests for the Canonical Enforcement Gate (/api/v1/enforce/evaluate_action)
==========================================================================
Validates:
  - ALLOW path: clean action + KNOWN epistemic state
  - DENY path: threatening action exceeding risk threshold
  - ABSTAIN path: UNKNOWN epistemic state
  - AMBIGUOUS + medium risk → DENY (conservative)
  - Trace hash determinism: same inputs → same hash
  - Schema validation: missing/invalid fields
  - All BHIV source systems accepted
  - Context signal aggregation (fail-high)
  - Replay verification: identical inputs → byte-identical output
"""

import pytest
import hashlib
import json
from app.enforcement_schemas import (
    EvaluateActionRequest,
    SarathiEvaluateResponse,
    ContextSignal,
    DGICEpistemicStateInput,
    SourceSystem,
    SarathiDecision,
)
from app.layer0_intelligence import aggregate_context_signals
from app.layer5_bucket import _replay_evaluate_action as evaluate_action
from app.layer1_sarathi import compute_trace_hash
from app.sutradhara_control_plane import _DENY_RISK_THRESHOLD as DENY_RISK_THRESHOLD, _AMBIGUOUS_DENY_THRESHOLD as AMBIGUOUS_DENY_THRESHOLD
from app.layer3_dgic import compute_envelope_hash


# ============================================================
# Helpers — Build valid DGIC state with correct cryptographic seal
# ============================================================

def _make_lineage_hash(seed: str = "test") -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _make_dgic_state(
    epistemic_state: str = "KNOWN",
    entropy_score: float = 0.1,
    contradiction_flag: bool = False,
    lineage_seed: str = "test-lineage",
) -> DGICEpistemicStateInput:
    """Build a valid DGIC epistemic state with correct cryptographic seal."""
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
    proposed_action: str = "Send a greeting message to the user",
    source_system: SourceSystem = SourceSystem.AI_BEING,
    dgic_state: DGICEpistemicStateInput | None = None,
    context_signals: list | None = None,
    execution_id: str = "action-001",
    actor: str = "test-actor",
) -> EvaluateActionRequest:
    """Build a valid enforcement request."""
    if dgic_state is None:
        dgic_state = _make_dgic_state()
    return EvaluateActionRequest(
        execution_id=execution_id,
        actor=actor,
        proposed_action=proposed_action,
        context_signals=context_signals or [],
        dgic_epistemic_state=dgic_state,
        source_system=source_system,
    )


# ============================================================
# ALLOW path tests
# ============================================================

class TestAllowPath:
    def test_clean_action_known_state_allows(self):
        """Clean action + KNOWN epistemic state → ALLOW."""
        req = _make_request(proposed_action="Prepare daily report summary")
        result = evaluate_action(req)
        assert result.sarathi_decision == SarathiDecision.ALLOW
        assert result.failure_reason is None
        assert result.risk_score >= 0.0
        assert result.confidence >= 0.0
        assert len(result.trace_hash) == 64

    def test_clean_action_inferred_state_allows(self):
        """Clean action + INFERRED epistemic state → ALLOW."""
        dgic = _make_dgic_state(epistemic_state="INFERRED", entropy_score=0.3)
        req = _make_request(proposed_action="Generate weather report", dgic_state=dgic)
        result = evaluate_action(req)
        assert result.sarathi_decision == SarathiDecision.ALLOW
        assert result.failure_reason is None

    def test_low_risk_action_with_context_signals_allows(self):
        """Low-risk action with low context signals → ALLOW."""
        signals = [
            ContextSignal(signal_id="s1", signal_type="environmental", value=0.1, source="sensor-a"),
            ContextSignal(signal_id="s2", signal_type="operational", value=0.15, source="sensor-b"),
        ]
        req = _make_request(proposed_action="Log sensor reading", context_signals=signals)
        result = evaluate_action(req)
        assert result.sarathi_decision == SarathiDecision.ALLOW


# ============================================================
# DENY path tests
# ============================================================

class TestDenyPath:
    def test_threatening_action_denied(self):
        """Threatening text in proposed action → DENY."""
        req = _make_request(
            proposed_action="kill the target and attack the base with bomb and shoot everyone"
        )
        result = evaluate_action(req)
        assert result.sarathi_decision == SarathiDecision.DENY
        assert result.failure_reason is not None
        assert result.risk_score >= DENY_RISK_THRESHOLD

    def test_high_context_signal_causes_deny(self):
        """High context signal (>= 0.7) → DENY regardless of clean text."""
        signals = [
            ContextSignal(signal_id="threat-1", signal_type="security_alert", value=0.85, source="insightbridge"),
        ]
        req = _make_request(proposed_action="Send greeting", context_signals=signals)
        result = evaluate_action(req)
        assert result.sarathi_decision == SarathiDecision.DENY
        assert result.failure_reason is not None

    def test_ambiguous_state_medium_risk_denied(self):
        """AMBIGUOUS epistemic state + risk >= 0.3 → DENY (conservative)."""
        dgic = _make_dgic_state(epistemic_state="AMBIGUOUS", entropy_score=0.5, contradiction_flag=False)
        # Use context signal to push risk above AMBIGUOUS_DENY_THRESHOLD
        signals = [
            ContextSignal(signal_id="s1", signal_type="anomaly", value=0.35, source="marine-sensor"),
        ]
        req = _make_request(
            proposed_action="Execute navigation correction",
            dgic_state=dgic,
            context_signals=signals,
        )
        result = evaluate_action(req)
        assert result.sarathi_decision == SarathiDecision.DENY
        assert "Ambiguous" in result.failure_reason or "ambiguous" in result.failure_reason.lower()


# ============================================================
# ABSTAIN path tests
# ============================================================

class TestAbstainPath:
    def test_unknown_epistemic_state_abstains(self):
        """UNKNOWN epistemic state → ABSTAIN."""
        dgic = _make_dgic_state(epistemic_state="UNKNOWN", entropy_score=0.0)
        req = _make_request(proposed_action="Run diagnostic scan", dgic_state=dgic)
        result = evaluate_action(req)
        assert result.sarathi_decision == SarathiDecision.ABSTAIN
        assert result.failure_reason is not None
        assert "abstention" in result.failure_reason.lower() or "UNKNOWN" in result.failure_reason

    def test_invalid_dgic_envelope_abstains(self):
        """Tampered DGIC envelope → ABSTAIN."""
        dgic = _make_dgic_state()
        # Tamper the envelope hash
        dgic_dict = dgic.model_dump()
        dgic_dict["envelope_hash"] = "a" * 64  # Invalid seal
        tampered_dgic = DGICEpistemicStateInput(**dgic_dict)
        req = _make_request(proposed_action="Normal action", dgic_state=tampered_dgic)
        result = evaluate_action(req)
        assert result.sarathi_decision == SarathiDecision.ABSTAIN
        assert "DGIC snapshot rejected" in result.failure_reason


# ============================================================
# Trace hash determinism
# ============================================================

class TestTraceHashDeterminism:
    def test_same_inputs_produce_same_trace_hash(self):
        """Identical inputs must produce identical trace hash."""
        req1 = _make_request(execution_id="act-99", actor="agent-alpha")
        req2 = _make_request(execution_id="act-99", actor="agent-alpha")
        hash1 = compute_trace_hash(req1)
        hash2 = compute_trace_hash(req2)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_different_inputs_produce_different_trace_hash(self):
        """Different inputs must produce different trace hash."""
        req1 = _make_request(execution_id="act-1")
        req2 = _make_request(execution_id="act-2")
        assert compute_trace_hash(req1) != compute_trace_hash(req2)

    def test_replay_produces_identical_output(self):
        """Same request evaluated twice → byte-identical response."""
        req = _make_request()
        result1 = evaluate_action(req)
        result2 = evaluate_action(req)
        assert result1.risk_score == result2.risk_score
        assert result1.sarathi_decision == result2.sarathi_decision
        assert result1.confidence == result2.confidence
        assert result1.failure_reason == result2.failure_reason
        assert result1.trace_hash == result2.trace_hash


# ============================================================
# Source system coverage
# ============================================================

class TestSourceSystemCoverage:
    @pytest.mark.parametrize("system", list(SourceSystem))
    def test_all_source_systems_accepted(self, system: SourceSystem):
        """Every BHIV source system must be accepted."""
        req = _make_request(source_system=system)
        result = evaluate_action(req)
        assert result.sarathi_decision in {
            SarathiDecision.ALLOW,
            SarathiDecision.DENY,
            SarathiDecision.ABSTAIN,
        }
        assert len(result.trace_hash) == 64


# ============================================================
# Context signal aggregation
# ============================================================

class TestContextSignalAggregation:
    def test_no_signals_returns_zero(self):
        """No context signals → 0.0 aggregate."""
        req = _make_request(context_signals=[])
        assert aggregate_context_signals(req.context_signals) == 0.0

    def test_non_insightbridge_max_signal_used(self):
        """Non-InsightBridge aggregation uses raw max (fail-high)."""
        signals = [
            ContextSignal(signal_id="a", signal_type="threat", value=0.2, source="s1"),
            ContextSignal(signal_id="b", signal_type="anomaly", value=0.8, source="s2"),
            ContextSignal(signal_id="c", signal_type="env", value=0.5, source="s3"),
        ]
        req = _make_request(context_signals=signals)
        assert aggregate_context_signals(req.context_signals) == 0.8

    def test_insightbridge_signals_are_weighted(self):
        """InsightBridge signals are mathematically weighted before max is taken."""
        signals = [
            # 0.8 * 0.5 (anomaly weight) = 0.4 weighted
            ContextSignal(signal_id="b", signal_type="anomaly_signal", value=0.8, source="INSIGHTBRIDGE"),
            # 0.6 * 1.0 (security alert weight) = 0.6 weighted
            ContextSignal(signal_id="c", signal_type="security_alert", value=0.6, source="INSIGHTBRIDGE"),
        ]
        req = _make_request(context_signals=signals)
        # Even though anomaly's raw 0.8 is higher than security_alert's 0.6,
        # the security_alert's weighted 0.6 wins over the anomaly's weighted 0.4
        assert aggregate_context_signals(req.context_signals) == 0.6
        
    def test_insightbridge_fallback_weight(self):
        """Unknown InsightBridge signal types fallback to 0.1 weight."""
        signals = [
            # 0.9 * 0.1 (unknown weight) = 0.09
            ContextSignal(signal_id="a", signal_type="made_up", value=0.9, source="INSIGHTBRIDGE"),
        ]
        req = _make_request(context_signals=signals)
        assert aggregate_context_signals(req.context_signals) == 0.09


# ============================================================
# Schema validation
# ============================================================

class TestSchemaValidation:
    def test_empty_execution_id_rejected(self):
        """Empty execution_id fails Pydantic validation."""
        with pytest.raises(Exception):
            _make_request(execution_id="")

    def test_empty_proposed_action_rejected(self):
        """Empty proposed_action fails Pydantic validation."""
        with pytest.raises(Exception):
            _make_request(proposed_action="")

    def test_invalid_source_system_rejected(self):
        """Invalid source_system fails Pydantic validation."""
        with pytest.raises(Exception):
            EvaluateActionRequest(
                execution_id="act-1",
                actor="test",
                proposed_action="test action",
                context_signals=[],
                dgic_epistemic_state=_make_dgic_state(),
                source_system="INVALID_SYSTEM",
            )

    def test_invalid_epistemic_state_rejected(self):
        """Invalid epistemic_state fails Pydantic validation."""
        with pytest.raises(Exception):
            DGICEpistemicStateInput(
                epistemic_state="MAYBE",
                entropy_score=0.5,
                contradiction_flag=False,
                lineage_hash="a" * 64,
                envelope_hash="b" * 64,
            )

    def test_signal_value_out_of_range_rejected(self):
        """Context signal value > 1.0 fails Pydantic validation."""
        with pytest.raises(Exception):
            ContextSignal(signal_id="s1", signal_type="threat", value=1.5, source="src")

    def test_response_has_all_required_fields(self):
        """Response contains all required fields with correct types."""
        req = _make_request()
        result = evaluate_action(req)
        assert isinstance(result.risk_score, float)
        assert isinstance(result.sarathi_decision, SarathiDecision)
        assert isinstance(result.confidence, float)
        assert isinstance(result.trace_hash, str)
        assert 0.0 <= result.risk_score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.trace_hash) == 64
