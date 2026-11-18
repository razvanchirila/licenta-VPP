"""In-memory sliding-window counters for the auth routes (the api runs as a single process)."""
from __future__ import annotations

import time
from collections import deque

MAX_KEYS = 10_000


class SlidingWindow:
    def __init__(self, window_seconds: float):
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}

    def _recent(self, key: str, now: float) -> deque[float]:
        hits = self._hits.get(key)
        if hits is None:
            return deque()
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        if not hits:
            del self._hits[key]
        return hits

    def count(self, key: str) -> int:
        return len(self._recent(key, time.monotonic()))

    def hit(self, key: str) -> None:
        now = time.monotonic()
        if len(self._hits) >= MAX_KEYS:
            for k in list(self._hits):
                self._recent(k, now)
        self._hits.setdefault(key, self._recent(key, now)).append(now)

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._hits.clear()
        else:
            self._hits.pop(key, None)


# failed logins per username, so the limit holds behind the reverse proxies (they hide the client IP)
login_failures = SlidingWindow(window_seconds=300)
registrations = SlidingWindow(window_seconds=3600)
