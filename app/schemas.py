from pydantic import BaseModel
from typing import List, Optional, Literal

class InputSchema(BaseModel):
    text: str

class ErrorSchema(BaseModel):
    error_code: str
    message: str

class SafetyMetadata(BaseModel):
    is_decision: Literal[False]
    authority: Literal["NONE"]
    actionable: Literal[False]

class OutputSchema(BaseModel):
    risk_score: float
    risk_category: str
    trigger_reasons: List[str]
    confidence_score: float
    processed_length: int
    safety_metadata: SafetyMetadata
    errors: Optional[ErrorSchema] = None
