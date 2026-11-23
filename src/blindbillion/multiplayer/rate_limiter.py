"""Thread-safe sliding-window rate limiter protecting room creation and joining."""

from __future__ import annotations

import threading
import time
from collections import defaultdict


class RateLimiter:
    """In-memory sliding window rate limiter."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, list[float]] = defaultdict(list)

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: float = 60.0) -> bool:
        """Check if request under `key` exceeds `max_requests` within `window_seconds`.

        Returns True if request is allowed, False if rate limit is exceeded.
        """
        now = time.monotonic()
        threshold = now - window_seconds

        with self._lock:
            timestamps = self._records[key]
            # Prune expired entries
            valid_timestamps = [t for t in timestamps if t > threshold]
            if len(valid_timestamps) >= max_requests:
                self._records[key] = valid_timestamps
                return False

            valid_timestamps.append(now)
            self._records[key] = valid_timestamps
            return True

    def reset(self) -> None:
        """Clear all rate limit tracking records."""
        with self._lock:
            self._records.clear()


# Global default rate limiter
global_rate_limiter = RateLimiter()
