import json
import hashlib
import uuid
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def compute_envelope_hash(version: str, lineage_hash: str, payload_dict: dict) -> str:
    payload_str = json.dumps(payload_dict, sort_keys=True)
    raw = f"{version}|{lineage_hash}|{payload_str}"
    return hashlib.sha256(raw.encode()).hexdigest()

def get_valid_dgic_envelope():
    lineage_hash = hashlib.sha256(b"test_evidence").hexdigest()
    payload = {
        "epistemic_state": "KNOWN",
        "entropy_score": 0.1,
        "contradiction_flag": False
    }
    envelope_hash = compute_envelope_hash("schema_v1", lineage_hash, payload)
    return {
        "version": "schema_v1",
        "lineage_hash": lineage_hash,
        "envelope_hash": envelope_hash,
        "payload": payload,
        "collapse_flag": False
    }

def safe_print_response(method, endpoint, response):
    try:
        data = response.json()
    except:
        data = response.text
    print(f"{method} {endpoint} ->", response.status_code, data, flush=True)
    return data

def test_endpoints():
    print("Testing /health", flush=True)
    r = client.get("/health")
    safe_print_response("GET", "/health", r)
    
    print("\nTesting /analyze", flush=True)
    r = client.post("/analyze", json={"text": "This is a benign text message"})
    safe_print_response("POST", "/analyze", r)
    
    print("\nTesting /api/v1/dgic/ingest", flush=True)
    dgic_env = get_valid_dgic_envelope()
    r = client.post("/api/v1/dgic/ingest", json={"text": "Benign text", "dgic_envelope": dgic_env})
    safe_print_response("POST", "/api/v1/dgic/ingest", r)

    print("\nTesting /api/v1/aggregate", flush=True)
    r = client.post("/api/v1/aggregate", json={"signals": [{"text": "sig1", "dgic_envelope": dgic_env}]})
    safe_print_response("POST", "/api/v1/aggregate", r)

    print("\nTesting /api/v1/aggregate/unified", flush=True)
    unified_req = {
        "signals": [{
            "signal_id": "sig-123",
            "signal_type": "TEXT_RISK_SIGNAL",
            "base_risk_score": 0.5,
            "base_confidence_score": 0.8,
            "dgic_envelope": dgic_env
        }]
    }
    r = client.post("/api/v1/aggregate/unified", json=unified_req)
    safe_print_response("POST", "/api/v1/aggregate/unified", r)
    
    print("\nTesting /api/v1/sutradhara/invoke", flush=True)
    sutra_req = {
        "actor": "system",
        "proposed_action": "test",
        "context_signals": [],
        "dgic_epistemic_state": {
            "state_snapshot_id": "snap-123",
            "epistemic_state": "KNOWN",
            "contradiction_flag": False,
            "entropy_score": 0.1,
            "lineage_hash": dgic_env["lineage_hash"],
            "envelope_hash": dgic_env["envelope_hash"],
            "entropy_boundary": "STABLE"
        },
        "source_system": "TEST_SYS"
    }
    r = client.post("/api/v1/sutradhara/invoke", json=sutra_req)
    safe_print_response("POST", "/api/v1/sutradhara/invoke", r)

    print("\nTesting /api/v1/bucket/entries", flush=True)
    r = client.get("/api/v1/bucket/entries")
    entries = safe_print_response("GET", "/api/v1/bucket/entries", r)
    
    print("\nTesting /api/v1/bucket/replay_all", flush=True)
    r = client.post("/api/v1/bucket/replay_all")
    safe_print_response("POST", "/api/v1/bucket/replay_all", r)
    
    if entries and isinstance(entries, list):
        trace_hash = entries[0].get("trace_hash")
        if trace_hash:
            print(f"\nTesting /api/v1/bucket/replay/{trace_hash}", flush=True)
            r = client.post(f"/api/v1/bucket/replay/{trace_hash}")
            safe_print_response("POST", f"/api/v1/bucket/replay/{trace_hash}", r)

    print("\nTesting /sarathi/validate-token", flush=True)
    params = {
        "execution_id": "test_exec_1",
        "rajya_verdict": "ALLOW",
        "token_status": "ACTIVE",
        "timestamp": datetime.utcnow().isoformat(),
        "signature_hash": "dummy_hash"
    }
    r = client.get("/sarathi/validate-token", params=params)
    safe_print_response("GET", "/sarathi/validate-token", r)
    
    print("\nTesting /sarathi/enforce", flush=True)
    enforce_req = {
        "token": params
    }
    r = client.post("/sarathi/enforce", json=enforce_req)
    safe_print_response("POST", "/sarathi/enforce", r)

if __name__ == "__main__":
    test_endpoints()
