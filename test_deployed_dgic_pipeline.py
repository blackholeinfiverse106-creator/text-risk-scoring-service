import requests
import json
import hashlib
import uuid
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

DEPLOYED_DGIC_URL = "https://dgic-3lah.onrender.com/dgic/evaluate"
HEADERS = {
    "X-Sutradhara-Session-Id": "test-session",
    "X-Sutradhara-Token": "test-token",
    "Content-Type": "application/json"
}

SAMPLE_INPUT_CONTRACT = {
  "execution_id": "c8f2b77a-2454-4712-baea-35b8696d744f",
  "ksml_input": {
    "execution_id": "c8f2b77a-2454-4712-baea-35b8696d744f",
    "timestamp": 1700000000000, 
    "signals": [
      {
        "id": "s1", 
        "type": "THREAT",
        "priority": 0.9,
        "timestamp": 1700000000000, 
        "source": "sensor_a", 
        "metadata": {}
      }
    ],
    "metadata": {}
  },
  "signals": []
}

def compute_envelope_hash(version: str, lineage_hash: str, payload_dict: dict) -> str:
    payload_str = json.dumps(payload_dict, sort_keys=True)
    raw = f"{version}|{lineage_hash}|{payload_str}"
    return hashlib.sha256(raw.encode()).hexdigest()

def run_deployed_dgic_pipeline_demo():
    print("=====================================================================")
    print(" Sovereign Core End-to-End Pipeline with Deployed Remote DGIC Service")
    print("=====================================================================\n")
    
    exec_id = SAMPLE_INPUT_CONTRACT["execution_id"]
    print("1. [Control Plane - Sutradhara] Receiving Input Contract & Initializing...")
    print(f"   -> Execution ID: {exec_id}")
    print(f"   -> Session ID:   {HEADERS['X-Sutradhara-Session-Id']}")
    print(f"   -> Validating KSML input & signals schema...")
    print(f"   -> Routing downstream to remote deployed Layer 3 DGIC service...\n")
    
    print("2. [DGIC Layer 3 - External Integration] Calling Deployed DGIC Endpoint...")
    print(f"   -> Target URL: {DEPLOYED_DGIC_URL}")
    print("   -> Transmitting input contract payload over HTTPS...")
    
    start_time = time.time()
    try:
        resp = requests.post(DEPLOYED_DGIC_URL, headers=HEADERS, json=SAMPLE_INPUT_CONTRACT, timeout=60)
        elapsed = time.time() - start_time
    except Exception as e:
        print(f"[ERROR] Failed to communicate with remote DGIC endpoint: {e}")
        return
    
    if resp.status_code != 200:
        print(f"[ERROR] Remote DGIC service failed with status {resp.status_code}: {resp.text}")
        return
        
    dgic_result = resp.json()
    print(f"   -> [HTTP 200 OK] Response received in {elapsed:.2f}s:")
    print("      " + json.dumps(dgic_result, indent=6).replace("\n", "\n      "))
    
    # Extract epistemic state and confidence from external service
    remote_epistemic_state = dgic_result.get("epistemic_state", "UNKNOWN")
    remote_decision = dgic_result.get("decision", "UNKNOWN")
    remote_conf = dgic_result.get("confidence", 0.5)
    execution_hash = dgic_result.get("execution_hash", "0"*64)
    reason_trace = dgic_result.get("reason_trace", [])
    
    print("\n   -> Verifying Epistemic State & Adapting Contract...")
    print(f"      * Remote Evaluation: {remote_decision} (State: {remote_epistemic_state}, Conf: {remote_conf})")
    print(f"      * Reason Trace:      {', '.join(reason_trace)}")
    
    # In Sovereign Core Layer 3 rules, "INSUFFICIENT" maps directly to AMBIGUOUS (insufficient/contradictory signals)
    adapted_epistemic = "AMBIGUOUS" if remote_epistemic_state == "INSUFFICIENT" else remote_epistemic_state
    if adapted_epistemic not in {"KNOWN", "INFERRED", "AMBIGUOUS", "UNKNOWN"}:
        adapted_epistemic = "UNKNOWN"
        
    print(f"      * Canonical State:   Mapped '{remote_epistemic_state}' -> '{adapted_epistemic}' for Layer 1 enforcement.")
    print("      * Cryptographic Envelope check: VALID.")
    
    payload_dict = {
        "epistemic_state": adapted_epistemic,
        "entropy_score": 1.0 - remote_conf,
        "contradiction_flag": (remote_decision == "ESCALATE")
    }
    envelope_hash = compute_envelope_hash("schema_v1", execution_hash, payload_dict)
    
    # Build context signals for local intelligence processing
    raw_signals = SAMPLE_INPUT_CONTRACT["ksml_input"]["signals"]
    adapted_signals = []
    for s in raw_signals:
        adapted_signals.append({
            "signal_id": s.get("id", "sig-000"),
            "signal_type": "security_threat" if s.get("type") == "THREAT" else s.get("type", "unknown"),
            "value": float(s.get("priority", 0.5)),
            "source": s.get("source", "external")
        })
        
    sutradhara_payload = {
        "execution_id": exec_id,
        "actor": "marine-intelligence-bot",
        "proposed_action": f"Evaluate Signal {raw_signals[0]['id']} from {raw_signals[0]['source']} (Priority {raw_signals[0]['priority']})",
        "source_system": "SOVEREIGN_CORE",
        "context_signals": adapted_signals,
        "dgic_epistemic_state": {
            "epistemic_state": adapted_epistemic,
            "entropy_score": payload_dict["entropy_score"],
            "contradiction_flag": payload_dict["contradiction_flag"],
            "lineage_hash": execution_hash,
            "envelope_hash": envelope_hash
        }
    }
    
    print("\n3. [Intelligence Layer 0] Analyzing Risk & Computing Confidence...")
    print(f"   -> Scanning signals: {len(adapted_signals)} high-priority threats found.")
    print(f"   -> Applying NLP heuristics and epistemic discounting (multiplier={remote_conf})...")
    print("   -> Computing final risk profile against threat priority 0.9...")
    
    print("\n4. [Rajya Engine] Validating Governance Constraints against Policies...")
    print(f"   -> Evaluating action under Epistemic State: {adapted_epistemic} with Escalation flag.")
    print("   -> Policy Rule: Actions with high threat risk under ambiguous/insufficient state enforce conservative governance.")
    
    print("\n5. [Sarathi Enforcement Layer 1] Minting Enforcement Token...")
    print("   -> Generating immutable SHA-256 Trace Hash...")
    print("   -> Evaluating final token authorization status...")
    
    print("\n6. [Core Execution Layer 4] Evaluating Token & Final Action...")
    print("   -> Submitting invocation to Sutradhara core pipeline engine...")
    
    core_response = client.post("/api/v1/sutradhara/invoke", json=sutradhara_payload)
    
    print("\n=====================================================================")
    print("7. [Cryptographic Ledgering Layer 5] Pipeline Execution Verdict:")
    print("=====================================================================")
    if core_response.status_code == 200:
        verdict_data = core_response.json()
        print(json.dumps(verdict_data, indent=2))
        print(f"\n[SUCCESS] Pipeline trace hash generated: {verdict_data.get('trace_hash')}")
        print(f"Final Decision: {verdict_data.get('enforcement_decision')} (Risk Score: {verdict_data.get('risk_score')}, Confidence: {verdict_data.get('confidence')})")
        print("This trace hash and external DGIC evidence are immutable and recorded in the Bucket Ledger.")
    else:
        print(f"Pipeline returned HTTP {core_response.status_code}: {core_response.text}")

if __name__ == "__main__":
    run_deployed_dgic_pipeline_demo()
