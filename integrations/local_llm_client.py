from typing import Dict, Any

class LocalLLMClient:
    def __init__(self, seed: int = 42):
        self.seed = seed
        
    def generate_response(self, prompt: str) -> str:
        # Completely deterministic mocked LLM response based on prompt content
        if "critical" in prompt.lower():
            return "THREAT_DETECTED"
        return "SAFE_TO_PROCEED"
