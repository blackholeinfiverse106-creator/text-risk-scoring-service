import pytest
import logging
import io
import json
from app.engine import analyze_text

def replay_score_from_logs(log_content: str) -> float:
    """
    Reconstructs the risk score purely by parsing the log stream (JSON format).
    Simulates an 'Audit Replay' of the decision.
    """
    category_scores = {}
    
    # Constants from Contract (Must match engine)
    KEYWORD_WEIGHT = 0.2
    MAX_CATEGORY_SCORE = 0.6
    MAX_TOTAL_SCORE = 1.0
    
    for line in log_content.splitlines():
        try:
            log_entry = json.loads(line)
        except json.JSONDecodeError:
            continue
            
        event_type = log_entry.get("event_type")
        details = log_entry.get("details", {})
        
        if event_type == "keyword_detected":
            cat = details.get("category")
            if cat:
                category_scores[cat] = category_scores.get(cat, 0.0) + KEYWORD_WEIGHT
                
        elif event_type == "category_capped":
            cat = details.get("category")
            if cat:
                # If capped, force score to max
                category_scores[cat] = MAX_CATEGORY_SCORE
                
    # Sum up categories
    total_score = sum(category_scores.values())
    
    # Apply global clamp if needed (implied by design, but engine logs it too)
    if total_score > MAX_TOTAL_SCORE:
        total_score = MAX_TOTAL_SCORE
        
    return round(total_score, 2)

def test_audit_log_completeness():
    """
    Verifies that the logs contain sufficient information to reconstruct the risk score.
    Now supports JSON structured logging.
    """
    # 1. Setup Capture
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    # JsonFormatter is already configured on root logger in main.py, 
    # but for this test we need to capture the output of *our* fixture or the app's logger.
    # Since analyze_text uses 'app.engine' logger which propagates to root,
    # we can just attach a basic handler to root and rely on the fact that log records 
    # are already formatted *if* we attached a formatter, OR we can attach our own JsonFormatter here.
    
    from app.observability import JsonFormatter
    handler.setFormatter(JsonFormatter())
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    try:
        # 2. Run Analysis (Complex Trace)
        # 3 keywords in 'violence' (0.6 -> CAPPED)
        # 1 keyword in 'fraud' (0.2)
        # Total expecting: 0.6 + 0.2 = 0.8 / HIGH
        text = "kill murder attack scam" 
        result = analyze_text(text, correlation_id="AUDIT-TEST-001")
        
        # 3. Get Logs
        log_contents = log_capture.getvalue()
        print("\nCaptured Logs:\n", log_contents) # Debug output
        
        # 4. Replay / Reconstruct
        reconstructed_score = replay_score_from_logs(log_contents)
        
        # 5. Assert Integrity
        assert result["risk_score"] == 0.8
        assert reconstructed_score == 0.8
        
        # Verify specific events exist in JSON
        assert "keyword_detected" in log_contents
        assert "category_capped" in log_contents
        assert "violence" in log_contents
        
    finally:
        root_logger.removeHandler(handler)
