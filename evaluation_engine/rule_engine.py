import hashlib
import json
from typing import Dict, Any

def evaluate_rules(input_data: Dict[str, Any]) -> Dict[str, Any]:
    # A deterministic rule engine
    score = 0
    if input_data.get("risk_level") == "high":
        score += 50
    if "urgent" in str(input_data.get("text", "")).lower():
        score += 30
        
    state = {
        "input": input_data,
        "score": score,
        "evaluated": True
    }
    
    # Compute SHA-256 state hash for determinism guarantee
    state_str = json.dumps(state, sort_keys=True)
    state_hash = hashlib.sha256(state_str.encode("utf-8")).hexdigest()
    
    return {
        "result": state,
        "state_hash": state_hash
    }
