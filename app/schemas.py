from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any

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

class DGICIngestRequest(BaseModel):
    text: str
    dgic_envelope: Dict[str, Any]

class AggregateRequest(BaseModel):
    signals: List[DGICIngestRequest]

class RajyaValidationRequest(BaseModel):
    execution_id: str
    sarathi_decision: Optional[str] = None
    sarathi_execution_id: Optional[str] = None
    enforcement_verdict: Optional[Dict[str, Any]] = None
