"""
Tests for Replay Verifier
===========================
Validates deterministic replay verification of bucket entries.
"""

import os
import hashlib
import pytest
from app.bucket_ledger import BucketLedger, BucketEntry
from app.replay_verifier import verify_bucket_entry, ReplayResult
from app.enforcement_schemas import (
    EvaluateActionRequest,
    DGICEpistemicStateInput,
    SourceSystem,
)
from app.enforcement_gate import evaluate_action
from app.enforcement_ledger import clear_ledger
from app.dgic_adapter import compute_envelope_hash

# Isolated bucket for replay tests
TEST_BUCKET_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "test_replay_bucket.jsonl",
)


def _make_lineage_hash(seed: str = "replay-test") -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _make_dgic_state(
    epistemic_state: str = "KNOWN",
    entropy_score: float = 0.1,
) -> DGICEpistemicStateInput:
    lineage_hash = _make_lineage_hash("replay-lineage")
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
def clean_memory_ledger():
    clear_ledger()
    yield
    clear_ledger()


class TestReplayVerification:
    def test_replay_produces_identical_decision(self):
        """Replaying a valid bucket entry yields byte-identical output."""
        dgic = _make_dgic_state()
        request = EvaluateActionRequest(
            action_id="replay-001",
            actor="test-agent",
            proposed_action="Generate report",
            context_signals=[],
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.AI_BEING,
        )

        # Evaluate once to get the original result
        result = evaluate_action(request)

        # Create a bucket entry from the result
        entry = BucketEntry(
            bucket_id="test-bucket-001",
            action_id="replay-001",
            timestamp_utc="2026-03-24T12:00:00+00:00",
            input_snapshot_hash="a" * 64,
            request_payload=request.model_dump(mode="json"),
            dgic_snapshot={},
            decision=result.enforcement_decision.value,
            risk_score=result.risk_score,
            confidence=result.confidence,
            failure_reason=result.failure_reason,
            trace_hash=result.trace_hash,
            trace_lineage="GENESIS",
            replay_proof="b" * 64,  # Dummy proof; will be checked separately
        )

        # Verify replay
        replay_result = verify_bucket_entry(entry)
        assert isinstance(replay_result, ReplayResult)
        assert replay_result.match is True
        assert replay_result.original_decision == replay_result.replayed_decision
        assert replay_result.original_risk_score == replay_result.replayed_risk_score

    def test_tampered_entry_fails_replay_proof(self):
        """Tampered replay_proof is detected."""
        dgic = _make_dgic_state()
        request = EvaluateActionRequest(
            action_id="replay-002",
            actor="test-agent",
            proposed_action="Generate report",
            context_signals=[],
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.AI_BEING,
        )
        result = evaluate_action(request)

        entry = BucketEntry(
            bucket_id="test-bucket-002",
            action_id="replay-002",
            timestamp_utc="2026-03-24T12:00:00+00:00",
            input_snapshot_hash="a" * 64,
            request_payload=request.model_dump(mode="json"),
            dgic_snapshot={},
            decision=result.enforcement_decision.value,
            risk_score=result.risk_score,
            confidence=result.confidence,
            failure_reason=result.failure_reason,
            trace_hash=result.trace_hash,
            trace_lineage="GENESIS",
            replay_proof="tampered_proof_hash_" + "x" * 44,  # Wrong proof
        )

        replay_result = verify_bucket_entry(entry)
        assert replay_result.replay_proof_valid is False
