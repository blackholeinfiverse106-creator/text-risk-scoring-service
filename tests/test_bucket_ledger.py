"""
Tests for Bucket Ledger
========================
Validates persistent JSONL storage, trace lineage chain, replay proof, and input snapshot hash.
"""

import os
import hashlib
import pytest
from app.bucket_ledger import (
    BucketLedger,
    BucketEntry,
    compute_input_snapshot_hash,
    compute_replay_proof,
)
from app.enforcement_schemas import (
    EvaluateActionRequest,
    DGICEpistemicStateInput,
    SourceSystem,
    ContextSignal,
)
from app.enforcement_gate import evaluate_action
from app.enforcement_ledger import clear_ledger
from app.dgic_adapter import compute_envelope_hash

# Test with isolated bucket file
TEST_BUCKET_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "test_enforcement_bucket.jsonl",
)


def _make_lineage_hash(seed: str = "bucket-test") -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _make_dgic_state(
    epistemic_state: str = "KNOWN",
    entropy_score: float = 0.1,
) -> DGICEpistemicStateInput:
    lineage_hash = _make_lineage_hash("bucket-lineage")
    payload_dict = {
        "epistemic_state": epistemic_state,
        "entropy_score": entropy_score,
        "contradiction_flag": False,
    }
    envelope_hash = compute_envelope_hash("schema_v1", lineage_hash, payload_dict)
    return DGICEpistemicStateInput(
        epistemic_state=epistemic_state,
        entropy_score=entropy_score,
        contradiction_flag=False,
        lineage_hash=lineage_hash,
        envelope_hash=envelope_hash,
    )


@pytest.fixture(autouse=True)
def isolated_bucket():
    """Use an isolated bucket file for each test."""
    ledger = BucketLedger(file_path=TEST_BUCKET_FILE)
    ledger.clear()
    yield ledger
    ledger.clear()


@pytest.fixture(autouse=True)
def clean_memory_ledger():
    clear_ledger()
    yield
    clear_ledger()


class TestBucketWriteRead:
    def test_write_and_read_roundtrip(self, isolated_bucket):
        """Write a bucket entry and read it back."""
        entry = isolated_bucket.write(
            action_id="act-001",
            request_payload={"test": "data"},
            dgic_snapshot={"snapshot_id": "snap-001"},
            decision="ALLOW",
            risk_score=0.1,
            confidence=0.9,
            failure_reason=None,
            trace_hash="a" * 64,
        )
        assert isinstance(entry, BucketEntry)
        assert entry.action_id == "act-001"
        assert entry.decision == "ALLOW"

        entries = isolated_bucket.read_all()
        assert len(entries) == 1
        assert entries[0].action_id == "act-001"

    def test_input_snapshot_hash_is_deterministic(self):
        """Same inputs → same snapshot hash."""
        req = {"action_id": "a1"}
        dgic = {"state": "KNOWN"}
        h1 = compute_input_snapshot_hash(req, dgic)
        h2 = compute_input_snapshot_hash(req, dgic)
        assert h1 == h2
        assert len(h1) == 64


class TestTraceLineage:
    def test_first_entry_has_genesis_lineage(self, isolated_bucket):
        """First entry in the chain has trace_lineage = GENESIS."""
        entry = isolated_bucket.write(
            action_id="act-001",
            request_payload={}, dgic_snapshot={},
            decision="ALLOW", risk_score=0.1, confidence=0.9,
            failure_reason=None, trace_hash="a" * 64,
        )
        assert entry.trace_lineage == "GENESIS"

    def test_second_entry_chains_to_first(self, isolated_bucket):
        """Second entry's trace_lineage points to first entry's bucket_id."""
        first = isolated_bucket.write(
            action_id="act-001",
            request_payload={}, dgic_snapshot={},
            decision="ALLOW", risk_score=0.1, confidence=0.9,
            failure_reason=None, trace_hash="a" * 64,
        )
        second = isolated_bucket.write(
            action_id="act-002",
            request_payload={}, dgic_snapshot={},
            decision="DENY", risk_score=0.8, confidence=0.9,
            failure_reason="High risk", trace_hash="b" * 64,
        )
        assert second.trace_lineage == first.bucket_id


class TestReplayProof:
    def test_replay_proof_detects_tampering(self, isolated_bucket):
        """If entry data changes, replay_proof recomputation yields a different hash."""
        entry = isolated_bucket.write(
            action_id="act-001",
            request_payload={"key": "value"}, dgic_snapshot={},
            decision="ALLOW", risk_score=0.1, confidence=0.9,
            failure_reason=None, trace_hash="a" * 64,
        )
        # Recompute proof from original data
        entry_dict = {
            "bucket_id": entry.bucket_id,
            "action_id": entry.action_id,
            "timestamp_utc": entry.timestamp_utc,
            "input_snapshot_hash": entry.input_snapshot_hash,
            "request_payload": entry.request_payload,
            "dgic_snapshot": entry.dgic_snapshot,
            "decision": entry.decision,
            "risk_score": entry.risk_score,
            "confidence": entry.confidence,
            "failure_reason": entry.failure_reason,
            "trace_hash": entry.trace_hash,
            "trace_lineage": entry.trace_lineage,
        }
        assert compute_replay_proof(entry_dict) == entry.replay_proof

        # Tamper with data
        entry_dict["decision"] = "DENY"
        assert compute_replay_proof(entry_dict) != entry.replay_proof


class TestBucketLookup:
    def test_get_by_trace_hash(self, isolated_bucket):
        """Lookup a specific entry by trace hash."""
        isolated_bucket.write(
            action_id="act-001",
            request_payload={}, dgic_snapshot={},
            decision="ALLOW", risk_score=0.1, confidence=0.9,
            failure_reason=None, trace_hash="x" * 64,
        )
        found = isolated_bucket.get_by_trace_hash("x" * 64)
        assert found is not None
        assert found.action_id == "act-001"

    def test_get_by_trace_hash_not_found(self, isolated_bucket):
        """Returns None for missing trace hash."""
        assert isolated_bucket.get_by_trace_hash("z" * 64) is None
