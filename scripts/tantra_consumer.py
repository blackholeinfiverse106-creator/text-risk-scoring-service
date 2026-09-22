import requests
import json
import uuid
import time
import os
import random

API_URL = os.environ.get("SUTRADHARA_API_URL", "http://localhost:8000/api/v1/sutradhara/invoke")

def main():
    print("=" * 80)
    print(" [*] BHIV/TANTRA CONSUMER PLUG-AND-PLAY MOCK")
    print("=" * 80)
    
    execution_id = f"tantra-consumer-trace-{uuid.uuid4().hex[:6]}"
    
    payload = {
        "execution_id": execution_id,
        "actor": "tantra-external-consumer-02",
        "proposed_action": "Migrate sovereign data tier to external cluster",
        "context_signals": [
            {
                "signal_id": f"sig-{random.randint(100,999)}",
                "signal_type": "TEXT_ANALYSIS",
                "value": 0.45,
                "source": "tantra-sensor"
            }
        ],
        "dgic_epistemic_state": {
            "epistemic_state": "KNOWN",
            "entropy_score": 0.1,
            "contradiction_flag": False,
            "lineage_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "envelope_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        },
        "source_system": "SOVEREIGN_CORE"
    }

    print(f"[*] Attaching to Sovereign Core via Canonical Contract...")
    print(f"[*] Endpoint: {API_URL}")
    print(f"[*] Exec ID : {execution_id}\n")
    print("Request Payload:")
    print(json.dumps(payload, indent=2))
    
    print("\n[>] Dispatching payload to Sutradhara...")
    start_time = time.time()
    
    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        elapsed = time.time() - start_time
        
        print(f"\n[<] Received Response ({response.status_code}) in {elapsed:.2f}s")
        if response.ok:
            data = response.json()
            print("\n[+] Sovereign Core Executed Successfully")
            print("-" * 40)
            print(f"Verdict        : {data.get('enforcement_decision')}")
            print(f"Risk Score     : {data.get('risk_score')}")
            print(f"Trace Hash     : {data.get('trace_hash')}")
            if data.get('failure_reason'):
                print(f"Failure Reason : {data.get('failure_reason')}")
        else:
            print("\n[-] Pipeline Error")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"\n[-] Network Error: Could not connect to {API_URL}")
        print(f"Error: {e}")
        print("Please ensure the FastAPI backend is running (python run_backend.py)")

if __name__ == "__main__":
    main()
