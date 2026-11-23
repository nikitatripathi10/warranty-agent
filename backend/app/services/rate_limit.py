"""
Per-user / per-IP API rate limiter (in-memory sliding window).

Protects expensive LLM, Gmail and upload endpoints from accidental loops or
external abuse without requiring Redis on single-node deployments.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from typing import Optional


class RateLimiter:
    """Thread-safe sliding window rate limiter keyed by arbitrary string."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, now: Optional[float] = None) -> tuple[bool, int]:
        """Return ``(allowed, retry_after_seconds)``."""
        ts = time.monotonic() if now is None else now
        with self._lock:
            q = self._events.setdefault(key, deque())
            while q and ts - q[0] > self.window_seconds:
                q.popleft()
            if len(q) >= self.limit:
                retry_after = max(1, math.ceil(self.window_seconds - (ts - q[0])))
                return False, retry_after
            q.append(ts)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


_LIMITS: dict[tuple[str, str], RateLimiter] = {
    ("POST", "/ingestion/upload"): RateLimiter(20, 3600),
    ("POST", "/ingestion/fetch-emails"): RateLimiter(10, 3600),
    ("POST", "/extraction/test"): RateLimiter(30, 3600),
    ("POST", "/agent/query"): RateLimiter(40, 3600),
    ("POST", "/auth/gmail/email-connect"): RateLimiter(15, 3600),
}


def check_request_rate_limit(
    method: str, path: str, client_key: str, now: Optional[float] = None
) -> tuple[bool, int]:
    """Check whether ``(method, path)`` is under the cap for ``client_key``."""
    clean = path.rstrip("/") or "/"
    limiter = _LIMITS.get((method.upper(), clean))
    if limiter is None:
        return True, 0
    return limiter.check(f"{clean}:{client_key}", now=now)


def reset_all_limiters() -> None:
    for limiter in _LIMITS.values():
        limiter.reset()

