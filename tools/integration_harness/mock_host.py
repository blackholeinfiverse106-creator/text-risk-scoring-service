import sys
import os
# Fix path to allow importing app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.engine import analyze_text

def mock_policy_layer(user_input: str, user_is_trusted: bool):
    """
    The 'Two-Key' Logic Pattern:
    1. Key 1: Risk Signal (from Engine)
    2. Key 2: Business Logic (User Trust Level)
    """
    print(f"--- Processing Input: '{user_input}' (Trusted: {user_is_trusted}) ---")
    
    # 1. Get Signal
    signal = analyze_text(user_input)
    print(f"Signal: Score={signal['risk_score']} Category={signal['risk_category']}")
    
    # 2. Apply Policy (The "Action" is here, NOT in the engine)
    action = "ALLOW"
    
    if signal["risk_category"] == "HIGH":
        if user_is_trusted:
            action = "FLAG_FOR_REVIEW" # Trusted users get benefit of doubt
        else:
            action = "BLOCK" # Untrusted users blocked on High Risk
            
    elif signal["risk_category"] == "MEDIUM":
        action = "shadow_ban" if not user_is_trusted else "ALLOW"
        
    print(f"DECISION: {action}")
    print("--------------------------------------------------\n")
    return action

if __name__ == "__main__":
    # Scenario A: High Risk, Untrusted -> BLOCK
    mock_policy_layer("kill everyone now", user_is_trusted=False)
    
    # Scenario B: High Risk, Trusted -> REVIEW
    mock_policy_layer("kill everyone now", user_is_trusted=True)
    
    # Scenario C: Low Risk -> ALLOW
    mock_policy_layer("hello world", user_is_trusted=False)
