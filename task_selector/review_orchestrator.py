from evaluation_engine.rule_engine import evaluate_rules
from integrations.local_llm_client import LocalLLMClient
from typing import Dict, Any

def orchestrate_review(task_data: Dict[str, Any]) -> Dict[str, Any]:
    llm = LocalLLMClient()
    llm_analysis = llm.generate_response(task_data.get("text", ""))
    
    # Inject LLM analysis into rule engine
    task_data["llm_analysis"] = llm_analysis
    
    engine_result = evaluate_rules(task_data)
    
    return {
        "status": "COMPLETED",
        "llm_analysis": llm_analysis,
        "rule_engine_output": engine_result
    }
