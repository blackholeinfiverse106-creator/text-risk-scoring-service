from datetime import datetime
from .feedback_event import FeedbackEvent


def ingest_feedback(
    input_text_id: str,
    predicted_category: str,
    actual_outcome: str,
    affected_category: str
) -> FeedbackEvent:
    """
    Creates a validated, immutable feedback event.
    """

    if actual_outcome not in {"SAFE", "RISK_CONFIRMED"}:
        raise ValueError("Invalid actual outcome")

    return FeedbackEvent(
        timestamp=datetime.utcnow(),
        input_text_id=input_text_id,
        predicted_category=predicted_category,
        actual_outcome=actual_outcome,
        affected_category=affected_category
    )
