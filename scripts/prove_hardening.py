import sys
import os
import json
import uuid
from unittest.mock import patch
import traceback
import hashlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.sutradhara_control_plane import invoke_agent, ControlPlaneHardFailure
from app.enforcement_schemas import KSMLInput
from app.layer4_enforcement import EnforcementHardFailure
from app.layer5_bucket import verify_all

def compute_dgic_envelope_hash(epistemic_state, entropy_score, contradiction_flag):
    payload_dict = {
        "epistemic_state": epistemic_state,
        "entropy_score": entropy_score,
        "contradiction_flag": contradiction_flag
    }
    payload_str = json.dumps(payload_dict, sort_keys=True)
    lineage_hash = "0"*64
    raw = f"schema_v1|{lineage_hash}|{payload_str}"
    return hashlib.sha256(raw.encode()).hexdigest()

def create_valid_ksml(exec_id="test", bad_hash=False):
    epistemic = "KNOWN"
    entropy = 0.1
    contradiction = False
    if bad_hash:
        envelope_hash = "0"*64
    else:
        envelope_hash = compute_dgic_envelope_hash(epistemic, entropy, contradiction)

    return KSMLInput(
        execution_id=exec_id,
        structured_signals=[],
        metadata={
            "actor": "user",
            "proposed_action": "test",
            "source_system": "SOVEREIGN_CORE",
            "dgic_epistemic_state": {
                "epistemic_state": epistemic,
                "entropy_score": entropy,
                "contradiction_flag": contradiction,
                "lineage_hash": "0"*64,
                "envelope_hash": envelope_hash
            }
        }
    )

def test_dgic_unavailable():
    print("--- Testing DGIC Unavailable (Invalid Hash) ---")
    ksml = create_valid_ksml("exec-dgic", bad_hash=True)
    result = invoke_agent(ksml)
    print(f"Result: {result.enforcement_decision.value}, Reason: {result.failure_reason}")

@patch('app.rajya_validation_engine.validate_execution_request')
def test_rajya_unavailable(mock_rajya):
    print("\n--- Testing RAJYA Unavailable ---")
    mock_rajya.side_effect = Exception("RAJYA is down")
    ksml = create_valid_ksml("exec-rajya")
    
    try:
        invoke_agent(ksml)
    except Exception as e:
        print(f"Exception propagated: {e}")

@patch('app.sutradhara_control_plane.execute_core_mandala')
def test_core_unavailable(mock_core):
    print("\n--- Testing Core Unavailable ---")
    mock_core.side_effect = Exception("Core execution failed")
    ksml = create_valid_ksml("exec-core")
    
    try:
        invoke_agent(ksml)
    except Exception as e:
        print(f"Exception propagated: {e}")

@patch('app.layer4_enforcement.enforce')
def test_trace_mismatch(mock_enforce):
    print("\n--- Testing Trace Mismatch (Execution ID Mismatch) ---")
    mock_enforce.side_effect = EnforcementHardFailure("EXECUTION_ID_MISMATCH", "Mismatch trace")
    ksml = create_valid_ksml("exec-trace")
    
    result = invoke_agent(ksml)
    print(f"Result: {result.enforcement_decision.value}, Reason: {result.failure_reason}")

def test_contract_mismatch():
    print("\n--- Testing Contract Mismatch ---")
    try:
        ksml = KSMLInput(
            execution_id="exec",
            structured_signals=[],
            metadata={"actor": "user"} # Missing required fields
        )
    except Exception as e:
        print(f"Contract failure caught: {type(e).__name__} - {str(e)[:100]}")

def test_replay_validation():
    print("\n--- Testing Replay Validation ---")
    results = verify_all()
    print(f"Verified {len(results)} bucket entries.")
    if results:
        print(f"Entry {results[0].execution_id} matched: {results[0].match}")

if __name__ == "__main__":
    test_dgic_unavailable()
    test_rajya_unavailable()
    test_core_unavailable()
    test_trace_mismatch()
    test_contract_mismatch()
    test_replay_validation()
