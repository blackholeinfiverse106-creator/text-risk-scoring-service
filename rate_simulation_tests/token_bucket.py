"""
rate_simulation_tests/token_bucket.py
=====================================
Reusable token bucket rate limiter with configurable parameters.
Thread-safe via threading.Lock.
"""

import time
import threading


class TokenBucket:
    """
    Token bucket rate limiter.

    capacity    — max tokens held at any time
    refill_rate — tokens added per second
    """

    def __init__(self, capacity: int = 100, refill_rate: float = 50.0):
        self.capacity      = capacity
        self.refill_rate   = refill_rate
        self._tokens       = float(capacity)
        self._last_refill  = time.monotonic()
        self._lock         = threading.Lock()
        self._accepted     = 0
        self._rejected     = 0

    def _refill(self):
        now     = time.monotonic()
        elapsed = now - self._last_refill
        added   = elapsed * self.refill_rate
        self._tokens = min(self.capacity, self._tokens + added)
        self._last_refill = now

    def allow(self) -> bool:
        with self._lock:
            self._refill()
            if self._tokens >= 1:
                self._tokens -= 1
                self._accepted += 1
                return True
            self._rejected += 1
            return False

    @property
    def stats(self):
        return {
            "accepted":       self._accepted,
            "rejected":       self._rejected,
            "tokens_current": round(self._tokens, 2),
            "rejection_rate": round(
                self._rejected / max(self._accepted + self._rejected, 1), 4
            ),
        }
