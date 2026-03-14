from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.signal_aggregator import SignalType

class UnifiedSignalInput(BaseModel):
    signal_id: str
    signal_type: SignalType
    base_risk_score: float = Field(..., ge=0.0, le=1.0)
    base_confidence_score: float = Field(..., ge=0.0, le=1.0)
    dgic_envelope: Dict[str, Any]

class UnifiedAggregateRequest(BaseModel):
    signals: List[UnifiedSignalInput]

