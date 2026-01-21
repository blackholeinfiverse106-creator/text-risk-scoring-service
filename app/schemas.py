from pydantic import BaseModel
from typing import List, Optional

class InputSchema(BaseModel):
    text: str

class ErrorSchema(BaseModel):
    error_code: str
    message: str

class OutputSchema(BaseModel):
    risk_score: float
    risk_category: str
    trigger_reasons: List[str]
    processed_length: int
    errors: Optional[ErrorSchema] = None
