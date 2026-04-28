"""
Tests for Replay Verifier
===========================
Validates deterministic replay verification of bucket entries fetched from external Bucket Service.
"""

import os
import hashlib
import pytest
from app.layer5_bucket import compute_artifact_hash
from app.layer5_bucket import verify_bucket_entry, ReplayResult
from app.enforcement_schemas import (
    EvaluateActionRequest,
    DGICEpistemicStateInput,
    SourceSystem,
)
from app.layer5_bucket import _replay_evaluate_action as evaluate_action
from app.layer3_dgic import compute_envelope_hash


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


class TestReplayVerification:
    def test_replay_produces_identical_decision(self):
        """Replaying a valid bucket artifact yields byte-identical output."""
        dgic = _make_dgic_state()
        request = EvaluateActionRequest(
            execution_id="replay-001",
            actor="test-agent",
            proposed_action="Generate report",
            context_signals=[],
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.AI_BEING,
        )

        # Evaluate once to get the original result
        result = evaluate_action(request)

        # Construct the artifact exactly as the external service expects
        artifact = {
            "artifact_id": "replay-001",
            "source_module_id": "bhiv_enforcement_gate",
            "schema_version": "1.0.0",
            "timestamp_utc": "2026-03-24T12:00:00+00:00",
            "artifact_type": "truth_event",
            "payload": {
                "request_payload": request.model_dump(mode="json"),
                "dgic_snapshot": {},
                "decision": result.sarathi_decision.value,
                "risk_score": result.risk_score,
                "confidence": result.confidence,
                "failure_reason": result.failure_reason,
                "trace_hash": result.trace_hash,
            }
        }
        # Seal it
        artifact["artifact_hash"] = compute_artifact_hash(artifact)

        # Verify replay
        replay_result = verify_bucket_entry(artifact)
        assert isinstance(replay_result, ReplayResult)
        assert replay_result.match is True
        assert replay_result.original_decision == replay_result.replayed_decision
        assert replay_result.original_risk_score == replay_result.replayed_risk_score
        assert replay_result.replay_proof_valid is True

    def test_tampered_entry_fails_replay_proof(self):
        """Tampered artifact hash is detected."""
        dgic = _make_dgic_state()
        request = EvaluateActionRequest(
            execution_id="replay-002",
            actor="test-agent",
            proposed_action="Generate report",
            context_signals=[],
            dgic_epistemic_state=dgic,
            source_system=SourceSystem.AI_BEING,
        )
        result = evaluate_action(request)

        artifact = {
            "artifact_id": "replay-002",
            "source_module_id": "bhiv_enforcement_gate",
            "schema_version": "1.0.0",
            "timestamp_utc": "2026-03-24T12:00:00+00:00",
            "artifact_type": "truth_event",
            "payload": {
                "request_payload": request.model_dump(mode="json"),
                "dgic_snapshot": {},
                "decision": result.sarathi_decision.value,
                "risk_score": result.risk_score,
                "trace_hash": result.trace_hash,
            },
            "artifact_hash": "bad_hash_data_" + "x" * 50
        }

        replay_result = verify_bucket_entry(artifact)
        assert replay_result.replay_proof_valid is False
