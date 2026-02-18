import pytest
import logging
import io
import re
from app.engine import analyze_text

# Regex to parse structured logs
# Format: "... | event_type=X | param=Y ..."
LOG_PATTERN = re.compile(r"event_type=([a-zA-Z_]+)")
KEYWORD_PATTERN = re.compile(r"category=([a-zA-Z_]+)")

def replay_score_from_logs(log_content: str) -> float:
    """
    Reconstructs the risk score purely by parsing the log stream.
    Simulates an 'Audit Replay' of the decision.
    """
    category_scores = {}
    current_category = None
    
    # Constants from Contract (Must match engine)
    KEYWORD_WEIGHT = 0.2
    MAX_CATEGORY_SCORE = 0.6
    MAX_TOTAL_SCORE = 1.0
    
    for line in log_content.splitlines():
        event_match = LOG_PATTERN.search(line)
        if not event_match:
            continue
            
        event_type = event_match.group(1)
        
        if event_type == "keyword_detected":
            cat_match = KEYWORD_PATTERN.search(line)
            if cat_match:
                cat = cat_match.group(1)
                category_scores[cat] = category_scores.get(cat, 0.0) + KEYWORD_WEIGHT
                
        elif event_type == "category_capped":
            cat_match = KEYWORD_PATTERN.search(line)
            if cat_match:
                cat = cat_match.group(1)
                # If capped, force score to max
                category_scores[cat] = MAX_CATEGORY_SCORE
                
    # Sum up categories
    total_score = sum(category_scores.values())
    
    # Apply global clamp if needed (implied by design, but engine logs it too)
    # We can assume the standard clamp 1.0
    if total_score > MAX_TOTAL_SCORE:
        total_score = MAX_TOTAL_SCORE
        
    return round(total_score, 2)

def test_audit_log_completeness():
    """
    Verifies that the logs contain sufficient information to reconstruct the risk score.
    """
    # 1. Setup Capture
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(logging.Formatter("%(message)s"))
    
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
        
        # 4. Replay / Reconstruct
        reconstructed_score = replay_score_from_logs(log_contents)
        
        # 5. Assert Integrity
        assert result["risk_score"] == 0.8
        assert reconstructed_score == 0.8
        
        # Verify specific events exist
        assert "event_type=keyword_detected" in log_contents
        assert "event_type=category_capped" in log_contents
        assert "category=violence" in log_contents
        
    finally:
        root_logger.removeHandler(handler)
