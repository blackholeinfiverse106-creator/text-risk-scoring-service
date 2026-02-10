from feedback.learning_history import LearningHistory
from feedback.feedback_event import FeedbackEvent
from datetime import datetime, timezone


def test_learning_history_append_only():
    history = LearningHistory()

    event1 = FeedbackEvent(
        timestamp=datetime.now(timezone.utc),
        input_text_id="1",
        predicted_category="LOW",
        actual_outcome="SAFE",
        affected_category="fraud"
    )

    event2 = FeedbackEvent(
        timestamp=datetime.now(timezone.utc),
        input_text_id="2",
        predicted_category="HIGH",
        actual_outcome="RISK_CONFIRMED",
        affected_category="violence"
    )

    history.append(event1)
    history.append(event2)

    events = history.all_events()

    assert len(events) == 2
    assert events[0] == event1
    assert events[1] == event2
