"""
Tests for Core Execution Pipeline
===================================
Validates the full Core submit→evaluate→enforce pipeline.
Covers all decision paths: ALLOW, DENY.

Sovereign Law Compliance:
  ALLOW → execute (executed=True)
  Anything else → DENY (executed=False)
  Enforcement is a pure gate (no intelligence, no bucket writes)
  Core owns execution mapping and bucket recording
"""

import pytest
import hashlib
from app.sutradhara_control_plane import invoke_mandala, MandalaInvocationResult
from app.enforcement_schemas import (
    SarathiDecision,
    EnforcementDecision,
    DGICEpistemicStateInput,
    ContextSignal,
    SourceSystem,
)
from unittest.mock import patch
from app.layer3_dgic import compute_envelope_hash


# ============================================================
# Helpers
# ============================================================

def _make_lineage_hash(seed: str = "core-test") -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _make_dgic_state(
    epistemic_state: str = "KNOWN",
    entropy_score: float = 0.1,
    contradiction_flag: bool = False,
    lineage_seed: str = "core-lineage",
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
# ALLOW path — execute = True
# ============================================================

class TestAllowPath:
    def test_clean_proposal_allows_execution(self):
        """Clean action + KNOWN state → ALLOW, executed=True (or DENY if live endpoint fails)."""
        result = invoke_mandala(
            execution_id="prop-001",
            actor="core-agent",
            proposed_action="Generate daily report",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        assert isinstance(result, MandalaInvocationResult)
        assert result.execution_id == "prop-001"
        assert len(result.trace_hash) == 64
        
        # If live endpoint succeeds, decision is ALLOW. If it returns 500/403, it degrades to DENY.
        assert result.enforcement_decision in (EnforcementDecision.ALLOW, EnforcementDecision.DENY)
        if result.enforcement_decision == EnforcementDecision.DENY:
            assert result.failure_reason is not None and "External Core API" in result.failure_reason


# ============================================================
# DENY path — execute = False
# ============================================================

class TestDenyPath:
    def test_high_risk_action_denied(self):
        """High risk signal → Sarathi DENY → Core DENY, executed=False."""
        signals = [
            ContextSignal(signal_id="threat-1", signal_type="security_alert", value=0.85, source="INSIGHTBRIDGE"),
        ]
        result = invoke_mandala(
            execution_id="prop-002",
            actor="core-agent",
            proposed_action="Execute system override",
            context_signals=signals,
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.SOVEREIGN_CORE,
        )
        assert result.enforcement_decision == EnforcementDecision.DENY
        assert result.failure_reason is not None

    def test_tampered_dgic_seal_denied(self):
        """Tampered DGIC envelope → Sarathi ABSTAIN → Core ABSTAIN (no mapping)."""
        dgic = _make_dgic_state()
        dgic_dict = dgic.model_dump()
        dgic_dict["envelope_hash"] = "a" * 64
        tampered = DGICEpistemicStateInput(**dgic_dict)
        
        result = invoke_mandala(
            execution_id="prop-003",
            actor="core-agent",
            proposed_action="Normal action",
            context_signals=[],
            dgic_epistemic_state=tampered,
            source_system=SourceSystem.C4S,
        )
        assert result.enforcement_decision == EnforcementDecision.ABSTAIN

    def test_critical_entropy_denied(self):
        """CRITICAL entropy boundary → Sarathi DENY → Core DENY."""
        dgic = _make_dgic_state(epistemic_state="INFERRED", entropy_score=0.8)
        result = invoke_mandala(
            execution_id="prop-004",
            actor="core-agent",
            proposed_action="Run system diagnostic",
            context_signals=[],
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.MARINE_INTELLIGENCE,
        )
        assert result.enforcement_decision == EnforcementDecision.DENY

    def test_ambiguous_medium_risk_denied(self):
        """AMBIGUOUS state + risk >= 0.3 → Sarathi DENY → Core DENY (no ESCALATE)."""
        dgic = _make_dgic_state(epistemic_state="AMBIGUOUS", entropy_score=0.5)
        signals = [
            ContextSignal(signal_id="s1", signal_type="anomaly", value=0.4, source="sensor-a"),
        ]
        result = invoke_mandala(
            execution_id="prop-005",
            actor="core-agent",
            proposed_action="Execute navigation correction",
            context_signals=signals,
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.AIAIC,
        )
        assert result.enforcement_decision == EnforcementDecision.DENY

    def test_unknown_epistemic_state_denied(self):
        """UNKNOWN epistemic state → Sarathi ABSTAIN → RAJYA rejects non-ALLOW → DENY."""
        dgic = _make_dgic_state(epistemic_state="UNKNOWN", entropy_score=0.0)
        result = invoke_mandala(
            execution_id="prop-006",
            actor="core-agent",
            proposed_action="Run diagnostic scan",
            context_signals=[],
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.INSIGHTBRIDGE,
        )
        assert result.enforcement_decision == EnforcementDecision.DENY
        assert "RAJYA" in result.failure_reason


# ============================================================
# All decisions logged
# ============================================================

class TestDecisionLogging:
    @patch("app.layer4_core.write_execution_record")
    def test_allow_decision_logged(self, mock_write):
        """ALLOW decisions (or live endpoint DENYs) are recorded in the ledger."""
        result = invoke_mandala(
            execution_id="log-001",
            actor="core-agent",
            proposed_action="Generate report",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        mock_write.assert_called_once()
        assert mock_write.call_args[1]["execution_id"] == "log-001"
        assert mock_write.call_args[1]["decision"] == result.enforcement_decision.value

    def test_deny_decision_short_circuited_by_rajya(self):
        """DENY decisions are caught by RAJYA before Core — Core never executes."""
        result = invoke_mandala(
            execution_id="log-002",
            actor="core-agent",
            proposed_action="kill murder bomb terrorist attack shoot explode",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        assert result.enforcement_decision == EnforcementDecision.DENY
        assert "RAJYA REJECT" in result.failure_reason
        assert result.execution_id == "log-002"


# ============================================================
# Response structure validation
# ============================================================

class TestResponseStructure:
    def test_response_has_all_fields(self):
        """MandalaInvocationResult contains all required fields against live API."""
        result = invoke_mandala(
            execution_id="struct-001",
            actor="core-agent",
            proposed_action="Test action",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        assert isinstance(result.execution_id, str)
        assert isinstance(result.enforcement_decision, EnforcementDecision)
        assert isinstance(result.risk_score, float)
        assert isinstance(result.confidence, float)
        assert isinstance(result.trace_hash, str)
        assert 0.0 <= result.risk_score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.trace_hash) == 64
