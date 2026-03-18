"""
Tests for Enforcement Ledger
============================
Validates deterministic recording of enforcement decisions and snapshot replayability.
"""

import pytest
from app.enforcement_ledger import (
    record_decision,
    get_ledger_entries,
    get_ledger_entry,
    clear_ledger,
    EnforcementLedgerEntry,
)
from app.dgic_snapshot_consumer import ingest_dgic_snapshot
from app.enforcement_schemas import (
    EvaluateActionRequest,
    EvaluateActionResponse,
    EnforcementDecision,
    DGICEpistemicStateInput,
    SourceSystem,
)
from app.dgic_adapter import compute_envelope_hash
import hashlib


@pytest.fixture(autouse=True)
def clean_ledger():
    clear_ledger()
    yield
    clear_ledger()


def _make_snapshot():
    lineage = hashlib.sha256(b"lineage").hexdigest()
    payload = {"epistemic_state": "KNOWN", "entropy_score": 0.1, "contradiction_flag": False}
    envelope = compute_envelope_hash("schema_v1", lineage, payload)
    return ingest_dgic_snapshot("KNOWN", 0.1, False, lineage, envelope)


def _make_request():
    lineage = hashlib.sha256(b"lineage").hexdigest()
    payload_dict = {"epistemic_state": "KNOWN", "entropy_score": 0.1, "contradiction_flag": False}
    envelope = compute_envelope_hash("schema_v1", lineage, payload_dict)
    
    dgic_input = DGICEpistemicStateInput(
        epistemic_state="KNOWN",
        entropy_score=0.1,
        contradiction_flag=False,
        lineage_hash=lineage,
        envelope_hash=envelope,
    )
    
    return EvaluateActionRequest(
        action_id="act-1",
        actor="test",
        proposed_action="test action",
        context_signals=[],
        dgic_epistemic_state=dgic_input,
        source_system=SourceSystem.AI_BEING,
    )


def _make_response():
    return EvaluateActionResponse(
        risk_score=0.1,
        enforcement_decision=EnforcementDecision.ALLOW,
        confidence=0.9,
        failure_reason=None,
        trace_hash="a" * 64,
    )


class TestEnforcementLedger:

    def test_record_decision(self):
        """Recording a decision creates a ledger entry."""
        req = _make_request()
        snap = _make_snapshot()
        res = _make_response()
        
        entry = record_decision("corr-1", "2024-01-01T00:00:00Z", req, snap, res)
        
        assert isinstance(entry, EnforcementLedgerEntry)
        assert entry.correlation_id == "corr-1"
        assert entry.action_id == "act-1"
        assert entry.decision == "ALLOW"
        assert entry.trace_hash == "a" * 64
        
        # Verify JSON serializable inputs
        assert isinstance(entry.request_payload, dict)
        assert isinstance(entry.dgic_snapshot, dict)
        assert entry.dgic_snapshot["snapshot_hash"] == snap.snapshot_hash

    def test_get_ledger_entries(self):
        """Can retrieve all ledger entries."""
        assert len(get_ledger_entries()) == 0
        
        record_decision("corr-1", "ts1", _make_request(), _make_snapshot(), _make_response())
        record_decision("corr-2", "ts2", _make_request(), _make_snapshot(), _make_response())
        
        entries = get_ledger_entries()
        assert len(entries) == 2
        assert entries[0].correlation_id == "corr-1"
        assert entries[1].correlation_id == "corr-2"

    def test_get_by_trace_hash(self):
        """Can look up entry by deterministic trace hash."""
        res_a = _make_response()
        res_b = EvaluateActionResponse(
            risk_score=0.9,
            enforcement_decision=EnforcementDecision.DENY,
            confidence=0.9,
            failure_reason="test",
            trace_hash="b" * 64,
        )
        
        record_decision("corr-1", "ts1", _make_request(), _make_snapshot(), res_a)
        record_decision("corr-2", "ts2", _make_request(), _make_snapshot(), res_b)
        
        entry = get_ledger_entry("b" * 64)
        assert entry is not None
        assert entry.correlation_id == "corr-2"
        assert entry.decision == "DENY"
        
        missing = get_ledger_entry("c" * 64)
        assert missing is None
