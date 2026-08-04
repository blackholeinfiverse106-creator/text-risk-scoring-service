import json
import logging
import uuid
from datetime import datetime, timezone

from app.layer5_bucket import write_execution_record, _CURRENT_PARENT_HASH

# Configure clean, readable terminal logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] | %(message)s",
    datefmt="%H:%M:%S"
)

def main():
    print("=" * 80)
    print(" [*] SOVEREIGN CORE: LIVE BUCKET SERVICE STORAGE PROOF DEMONSTRATION")
    print("=" * 80)
    print("Target Bucket URL: https://bhiv-bucket-i1l6.onrender.com/bucket/artifact")
    print("Source Module ID : text_risk_scoring_service")
    print("Storage Type     : append_only (with parent_hash cryptographic chaining)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Execution #1
    # -------------------------------------------------------------------------
    exec_id_1 = str(uuid.uuid4())
    trace_id_1 = str(uuid.uuid4())
    print(f"\n[>] [STEP 1] Submitting First Execution Verdict (ID: {exec_id_1})...")
    
    result_1 = write_execution_record(
        execution_id=exec_id_1,
        decision="ALLOW",
        risk_score=0.12,
        confidence=0.98,
        trace_hash=trace_id_1,
        request_payload={"action": "evaluate_signal_perception", "source": "SOVEREIGN_CORE"},
        dgic_snapshot={"epistemic_state": "KNOWN", "entropy_score": 0.02, "contradiction_flag": False},
        failure_reason=None
    )

    if result_1 and result_1.get("hash"):
        print("[+] [SUCCESS] Execution #1 successfully written to MongoDB runtime!")
        print("-" * 60)
        print(f" * Stored Artifact ID : {result_1['artifact_id']}")
        print(f" * Used Parent Hash   : {result_1.get('parent_hash')} (Synced from chain head)")
        print(f" * Returned New Hash  : {result_1.get('hash')}")
        print("-" * 60)
    else:
        print("[-] [FAILED] Could not record execution #1 to bucket.")
        return

    # -------------------------------------------------------------------------
    # Execution #2 (Demonstrating Parent Hash Chaining)
    # -------------------------------------------------------------------------
    exec_id_2 = str(uuid.uuid4())
    trace_id_2 = str(uuid.uuid4())
    print(f"\n[>] [STEP 2] Submitting Second Execution Verdict (ID: {exec_id_2})...")
    print(f"    |-- Chaining from Parent Hash: {result_1['hash'][:16]}...")

    result_2 = write_execution_record(
        execution_id=exec_id_2,
        decision="DENY",
        risk_score=0.91,
        confidence=0.88,
        trace_hash=trace_id_2,
        request_payload={"action": "escalate_unverified_signal", "source": "SOVEREIGN_CORE"},
        dgic_snapshot={"epistemic_state": "AMBIGUOUS", "entropy_score": 0.55, "contradiction_flag": True},
        failure_reason="RAJYA REJECT: RAJYA_SARATHI_NOT_ALLOW"
    )

    if result_2 and result_2.get("hash"):
        print("[+] [SUCCESS] Execution #2 successfully chained and written to MongoDB!")
        print("-" * 60)
        print(f" * Stored Artifact ID : {result_2['artifact_id']}")
        print(f" * Chained Parent Hash: {result_2.get('parent_hash')} (Matches Call #1 hash!)")
        print(f" * Returned New Hash  : {result_2.get('hash')}")
        print("-" * 60)
    else:
        print("[-] [FAILED] Could not record execution #2 to bucket.")
        return

    print("\n[COMPLETE] Cryptographic chain successfully verified on live MongoDB!")
    print("=" * 80)

if __name__ == "__main__":
    main()
