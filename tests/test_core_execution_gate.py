"""
Tests for Core Execution Gate
===============================
Validates the full Core submit→evaluate→map→execute pipeline.
Covers all decision paths: ALLOW, BLOCK, ESCALATE, REQUEST_MORE_DATA.
"""

import pytest
import hashlib
from app.core_execution_gate import submit_proposal, CoreExecutionResult
from app.enforcement_schemas import (
    SarathiDecision,
    EnforcementDecision,
    DGICEpistemicStateInput,
    ContextSignal,
    SourceSystem,
)
from app.enforcement_ledger import get_ledger_entries, clear_ledger
from app.dgic_adapter import compute_envelope_hash


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


@pytest.fixture(autouse=True)
def clean_ledger():
    clear_ledger()
    yield
    clear_ledger()


# ============================================================
# ALLOW path — execute = True
# ============================================================

class TestAllowPath:
    def test_clean_proposal_allows_execution(self):
        """Clean action + KNOWN state → ALLOW, executed=True."""
        result = submit_proposal(
            execution_id="prop-001",
            actor="core-agent",
            proposed_action="Generate daily report",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        assert isinstance(result, CoreExecutionResult)
        assert result.execution_decision == SarathiDecision.ALLOW
        assert result.executed is True
        assert result.gate_decision == SarathiDecision.ALLOW
        assert result.execution_id == "prop-001"
        assert len(result.trace_hash) == 64


# ============================================================
# BLOCK path — execute = False
# ============================================================

class TestBlockPath:
    def test_high_risk_action_blocks(self):
        """High risk signal → DENY → BLOCK, executed=False."""
        signals = [
            ContextSignal(signal_id="threat-1", signal_type="security_alert", value=0.85, source="INSIGHTBRIDGE"),
        ]
        result = submit_proposal(
            execution_id="prop-002",
            actor="core-agent",
            proposed_action="Execute system override",
            context_signals=signals,
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.SOVEREIGN_CORE,
        )
        assert result.execution_decision == EnforcementDecision.BLOCK
        assert result.executed is False
        assert result.gate_decision == SarathiDecision.DENY
        assert result.failure_reason is not None

    def test_tampered_dgic_seal_blocks(self):
        """Tampered DGIC envelope → ABSTAIN → BLOCK, executed=False."""
        dgic = _make_dgic_state()
        dgic_dict = dgic.model_dump()
        dgic_dict["envelope_hash"] = "a" * 64
        tampered = DGICEpistemicStateInput(**dgic_dict)
        
        result = submit_proposal(
            execution_id="prop-003",
            actor="core-agent",
            proposed_action="Normal action",
            context_signals=[],
            dgic_epistemic_state=tampered,
            source_system=SourceSystem.C4S,
        )
        assert result.execution_decision == EnforcementDecision.BLOCK
        assert result.executed is False
        assert result.gate_decision == SarathiDecision.ABSTAIN

    def test_critical_entropy_blocks(self):
        """CRITICAL entropy boundary → DENY → BLOCK."""
        dgic = _make_dgic_state(epistemic_state="INFERRED", entropy_score=0.8)
        result = submit_proposal(
            execution_id="prop-004",
            actor="core-agent",
            proposed_action="Run system diagnostic",
            context_signals=[],
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.MARINE_INTELLIGENCE,
        )
        assert result.execution_decision == EnforcementDecision.BLOCK
        assert result.executed is False


# ============================================================
# ESCALATE path — AMBIGUOUS + medium risk
# ============================================================

class TestEscalatePath:
    def test_ambiguous_medium_risk_escalates(self):
        """AMBIGUOUS state + risk >= 0.3 → DENY → ESCALATE."""
        dgic = _make_dgic_state(epistemic_state="AMBIGUOUS", entropy_score=0.5)
        signals = [
            ContextSignal(signal_id="s1", signal_type="anomaly", value=0.4, source="sensor-a"),
        ]
        result = submit_proposal(
            execution_id="prop-005",
            actor="core-agent",
            proposed_action="Execute navigation correction",
            context_signals=signals,
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.AIAIC,
        )
        assert result.execution_decision == EnforcementDecision.ESCALATE
        assert result.executed is False
        assert result.gate_decision == SarathiDecision.DENY
        assert "ambiguous" in result.failure_reason.lower() or "uncertainty" in result.failure_reason.lower()


# ============================================================
# REQUEST_MORE_DATA path — UNKNOWN epistemic state
# ============================================================

class TestRequestMoreDataPath:
    def test_unknown_epistemic_state_requests_data(self):
        """UNKNOWN epistemic state → ABSTAIN → REQUEST_MORE_DATA."""
        dgic = _make_dgic_state(epistemic_state="UNKNOWN", entropy_score=0.0)
        result = submit_proposal(
            execution_id="prop-006",
            actor="core-agent",
            proposed_action="Run diagnostic scan",
            context_signals=[],
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.INSIGHTBRIDGE,
        )
        assert result.execution_decision == EnforcementDecision.REQUEST_MORE_DATA
        assert result.executed is False
        assert result.gate_decision == SarathiDecision.ABSTAIN


# ============================================================
# All decisions logged
# ============================================================

class TestDecisionLogging:
    def test_allow_decision_logged(self):
        """ALLOW decisions are recorded in the ledger."""
        submit_proposal(
            execution_id="log-001",
            actor="core-agent",
            proposed_action="Generate report",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        entries = get_ledger_entries()
        assert len(entries) >= 1
        assert entries[-1].execution_id == "log-001"

    def test_block_decision_logged(self):
        """BLOCK decisions are recorded in the ledger."""
        submit_proposal(
            execution_id="log-002",
            actor="core-agent",
            proposed_action="kill everyone and destroy the building with explosives and attack",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        entries = get_ledger_entries()
        assert any(e.execution_id == "log-002" for e in entries)


# ============================================================
# Response structure validation
# ============================================================

class TestResponseStructure:
    def test_response_has_all_fields(self):
        """CoreExecutionResult contains all required fields."""
        result = submit_proposal(
            execution_id="struct-001",
            actor="core-agent",
            proposed_action="Test action",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        assert isinstance(result.execution_id, str)
        assert isinstance(result.execution_decision, EnforcementDecision)
        assert isinstance(result.executed, bool)
        assert isinstance(result.risk_score, float)
        assert isinstance(result.confidence, float)
        assert isinstance(result.trace_hash, str)
        assert isinstance(result.gate_decision, EnforcementDecision)
        assert 0.0 <= result.risk_score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.trace_hash) == 64
