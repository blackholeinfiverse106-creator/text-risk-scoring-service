import pytest
from evaluation_engine.rule_engine import evaluate_rules
from task_selector.review_orchestrator import orchestrate_review

def test_deterministic_execution_50_runs():
    """50 consecutive runs must produce identical SHA-256 state hashes."""
    base_input = {"task_id": "t-1", "text": "This is a critical urgent task", "risk_level": "high"}
    
    first_result = orchestrate_review(base_input.copy())
    first_hash = first_result["rule_engine_output"]["state_hash"]
    
    for _ in range(49):
        current_result = orchestrate_review(base_input.copy())
        assert current_result["rule_engine_output"]["state_hash"] == first_hash

def test_local_llm_client_output():
    base_input = {"task_id": "t-2", "text": "Just normal text", "risk_level": "low"}
    result = orchestrate_review(base_input)
    assert result["llm_analysis"] == "SAFE_TO_PROCEED"
    assert result["rule_engine_output"]["result"]["score"] == 0
