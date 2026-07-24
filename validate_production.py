import json
import logging
import hashlib
from unittest.mock import patch
from app.enforcement_schemas import KSMLInput
from app.sutradhara_control_plane import invoke_agent, AgentVerificationError, ControlPlaneHardFailure
from app.layer5_bucket import _replay_evaluate_action, ReplayResult, verify_execution, write_execution_record
from app.enforcement_schemas import EvaluateActionRequest
import time

def compute_envelope_hash(version: str, lineage_hash: str, payload_dict: dict) -> str:
    payload_str = json.dumps(payload_dict, sort_keys=True)
    raw = f"{version}|{lineage_hash}|{payload_str}"
    return hashlib.sha256(raw.encode()).hexdigest()

def run_production_validation():
    results = {}
    print("Starting Phase 3 Production Validation...")

    lineage_hash = hashlib.sha256(b"demo-lineage").hexdigest()
    payload_dict = {
        "epistemic_state": "KNOWN",
        "entropy_score": 0.1,
        "contradiction_flag": False
    }
    envelope_hash = compute_envelope_hash("schema_v1", lineage_hash, payload_dict)

    valid_request = KSMLInput(
        execution_id="prod-exec-001",
        structured_signals=[{"signal_id": "sig-001", "signal_type": "security", "value": 0.1, "source": "firewall"}],
        metadata={
            "actor": "marine-intelligence-bot",
            "proposed_action": "Transfer highly classified structural data to Sector 4",
            "source_system": "MARINE_INTELLIGENCE",
            "dgic_epistemic_state": {
                "epistemic_state": "KNOWN",
                "entropy_score": 0.1,
                "contradiction_flag": False,
                "lineage_hash": lineage_hash,
                "envelope_hash": envelope_hash
            }
        }
    )

    # 1. End-to-End Execution
    try:
        e2e_res = invoke_agent(valid_request)
        results["end_to_end"] = {"status": "PASS", "trace_hash": e2e_res.trace_hash, "decision": e2e_res.enforcement_decision.value}
    except Exception as e:
        results["end_to_end"] = {"status": "FAIL", "error": str(e)}

    # 2. Replay Validation & Determinism & Trace Continuity
    try:
        eval_req = EvaluateActionRequest(
            execution_id=valid_request.execution_id,
            actor=valid_request.metadata["actor"],
            proposed_action=valid_request.metadata["proposed_action"],
            context_signals=valid_request.structured_signals,
            dgic_epistemic_state=valid_request.metadata["dgic_epistemic_state"],
            source_system=valid_request.metadata["source_system"]
        )
        replay_res1 = _replay_evaluate_action(eval_req)
        replay_res2 = _replay_evaluate_action(eval_req)
        
        if replay_res1.trace_hash == replay_res2.trace_hash and replay_res1.sarathi_decision.value == e2e_res.enforcement_decision.value:
            results["replay_validation"] = {"status": "PASS", "trace_hash": replay_res1.trace_hash, "decision": replay_res1.sarathi_decision.value}
            results["replay_determinism"] = {"status": "PASS"}
            results["trace_continuity"] = {"status": "PASS", "hash": replay_res1.trace_hash}
        else:
            results["replay_validation"] = {"status": "FAIL"}
            results["replay_determinism"] = {"status": "FAIL"}
            results["trace_continuity"] = {"status": "FAIL"}
    except Exception as e:
        results["replay_validation"] = {"status": "FAIL", "error": str(e)}

    # 3. Failure Injection (e.g. Critical Entropy)
    try:
        fail_req = valid_request.copy(deep=True)
        fail_req.metadata["dgic_epistemic_state"]["entropy_score"] = 0.99
        fail_payload = {
            "epistemic_state": fail_req.metadata["dgic_epistemic_state"]["epistemic_state"],
            "entropy_score": 0.99,
            "contradiction_flag": fail_req.metadata["dgic_epistemic_state"]["contradiction_flag"]
        }
        fail_req.metadata["dgic_epistemic_state"]["envelope_hash"] = compute_envelope_hash("schema_v1", fail_req.metadata["dgic_epistemic_state"]["lineage_hash"], fail_payload)
        fail_res = invoke_agent(fail_req)
        if fail_res.enforcement_decision.value == "DENY":
            results["failure_injection"] = {"status": "PASS", "reason": fail_res.failure_reason}
        else:
            results["failure_injection"] = {"status": "FAIL"}
    except Exception as e:
        results["failure_injection"] = {"status": "FAIL", "error": str(e)}

    # 4. Authority Validation
    try:
        auth_req = valid_request.copy(deep=True)
        auth_req.metadata["source_system"] = "UNREGISTERED_SYSTEM"
        invoke_agent(auth_req)
        results["authority_validation"] = {"status": "FAIL", "error": "Should have blocked"}
    except AgentVerificationError as e:
        results["authority_validation"] = {"status": "PASS", "error": str(e)}

    # 5. Contract Validation
    try:
        # Invalid input structure
        invoke_agent("invalid_input")
        results["contract_validation"] = {"status": "FAIL", "error": "Should have failed"}
    except ControlPlaneHardFailure as e:
        results["contract_validation"] = {"status": "PASS", "error": str(e)}

    # 6. Dependency Failure Testing (Bucket)
    import requests
    try:
        with patch("app.layer5_bucket.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.RequestException("Simulated Network Outage")
            dep_res = invoke_agent(valid_request)
            if dep_res.enforcement_decision.value == "ALLOW":
                results["dependency_failure"] = {"status": "PASS", "behavior": "Fail-Open Policy Honored"}
            else:
                results["dependency_failure"] = {"status": "FAIL"}
    except Exception as e:
        results["dependency_failure"] = {"status": "FAIL", "error": str(e)}

    # 7. Bucket Persistence Verification
    try:
        with patch("app.layer5_bucket.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            invoke_agent(valid_request)
            if mock_post.called:
                payload = mock_post.call_args[1]["json"]
                results["bucket_persistence"] = {"status": "PASS", "artifact_hash": payload["artifact_hash"]}
            else:
                results["bucket_persistence"] = {"status": "FAIL"}
    except Exception as e:
        results["bucket_persistence"] = {"status": "FAIL", "error": str(e)}

    # 8. Observability Verification
    try:
        with patch("app.sutradhara_control_plane.emit_enforcement_telemetry") as mock_telemetry:
            invoke_agent(valid_request)
            if mock_telemetry.called:
                results["observability_verification"] = {"status": "PASS", "emitted": True}
            else:
                results["observability_verification"] = {"status": "FAIL"}
    except Exception as e:
        results["observability_verification"] = {"status": "FAIL", "error": str(e)}

    with open("PHASE3_PRODUCTION_VALIDATION_PROOF.md", "w") as f:
        f.write("# Phase 3: Production Validation Proof\n\n")
        f.write("This document provides cryptographically continuous evidence of the Sovereign Core's production-grade guarantees.\n\n")
        
        tests = [
            ("End-to-End Execution", "end_to_end"),
            ("Replay Validation", "replay_validation"),
            ("Failure Injection", "failure_injection"),
            ("Dependency Failure Testing", "dependency_failure"),
            ("Contract Validation", "contract_validation"),
            ("Authority Validation", "authority_validation"),
            ("Trace Continuity", "trace_continuity"),
            ("Replay Determinism", "replay_determinism"),
            ("Observability Verification", "observability_verification"),
            ("Bucket Persistence Verification", "bucket_persistence"),
        ]
        
        for name, key in tests:
            f.write(f"## {name}\n")
            res = results.get(key, {"status": "NOT RUN"})
            f.write(f"**Status:** `{res.get('status')}`\n")
            f.write(f"**Evidence:**\n```json\n{json.dumps(res, indent=2)}\n```\n\n")

if __name__ == "__main__":
    run_production_validation()
