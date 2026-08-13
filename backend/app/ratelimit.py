"""In-memory sliding-window rate limiter for the public /screen endpoint.

Fixes PRD issue #1. The PRD asks for both "rate limit /screen" (§9) and "run
every seeded message through the real /screen endpoint" (§8) — which fight each
other: 80 seed messages against a 10/minute cap is a 20-minute seed run or a
wall of 429s. The seeder presents a shared secret and is exempted.

In-memory is deliberate for a single-instance prototype: no Redis to stand up,
nothing else to deploy. It resets on restart and does not coordinate across
replicas, which is fine here and stated plainly rather than hidden.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request, status

from app.config import get_settings


@dataclass
class _Window:
    hits: deque[float]


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: dict[str, _Window] = defaultdict(lambda: _Window(deque()))

    def check(self, key: str) -> tuple[bool, int]:
        """Return (allowed, seconds_until_retry). Monotonic clock — never wall time."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        hits = self._buckets[key].hits

        while hits and hits[0] < cutoff:
            hits.popleft()

        if len(hits) >= self.limit:
            retry_after = max(1, int(hits[0] + self.window_seconds - now) + 1)
            return False, retry_after

        hits.append(now)
        return True, 0

    def reset(self) -> None:
        self._buckets.clear()


_settings = get_settings()
screen_limiter = SlidingWindowLimiter(
    limit=_settings.rate_limit_requests,
    window_seconds=_settings.rate_limit_window_seconds,
)


def client_ip(request: Request) -> str:
    """Best-effort client IP behind Render/Vercel's proxy.

    X-Forwarded-For is client-controllable, so this is a courtesy limit against
    casual hammering, not a security control. Said out loud because treating a
    spoofable header as authoritative is how people build limiters that don't
    limit.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_screen(
    request: Request,
    x_seed_token: str | None = Header(default=None, alias="X-Seed-Token"),
) -> None:
    """FastAPI dependency. Enforces the limit unless a valid seed token is present."""
    settings = get_settings()

    if settings.seed_token and x_seed_token == settings.seed_token:
        return

    allowed, retry_after = screen_limiter.check(client_ip(request))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message": (
                    f"Too many screening requests. Try again in {retry_after}s."
                ),
                "retryable": True,
            },
            headers={"Retry-After": str(retry_after)},
        )
