from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FeedbackEvent:
    timestamp: datetime
    input_text_id: str
    predicted_category: str
    actual_outcome: str
    affected_category: str
