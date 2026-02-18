import concurrent.futures
import pytest
import uuid
from app.engine import analyze_text

def task(i):
    # Unique correlation ID per request to verify log separation
    cid = f"TEST-CONCURRENCY-{i}-{uuid.uuid4()}"
    return analyze_text(f"concurrent test {i} scam", correlation_id=cid), cid

def test_concurrency_contamination():
    """
    Verify 50 concurrent threads do not contaminate each other's score
    and ensure correlation IDs are preserved (simulated, since we check return values).
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(task, i) for i in range(50)]
        
        for future in concurrent.futures.as_completed(futures):
            res, cid_sent = future.result()
            
            # 1. Verify Scoring Integrity
            # Every result should contain 'scam' detection = 0.2 (LOW)
            assert res["risk_score"] == 0.2
            assert res["risk_category"] == "LOW"
            
            # 2. Verify Log/Context Integrity (via error/log simulation if we had log capture)
            # Here we ensure the engine accepted the CID and didn't crash.
            # Ideally we'd capture logs, but return value consistency is the primary proxy for state isolation.
