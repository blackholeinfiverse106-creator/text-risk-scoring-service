from typing import List
from .feedback_event import FeedbackEvent


class LearningHistory:
    """
    Append-only learning history.
    """

    def __init__(self):
        self._events: List[FeedbackEvent] = []

    def append(self, event: FeedbackEvent):
        self._events.append(event)

    def all_events(self) -> List[FeedbackEvent]:
        return list(self._events)  # defensive copy

    def count(self) -> int:
        return len(self._events)
