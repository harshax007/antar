"""
Antar — Simple Rate Limiter
=================================
In-process token bucket rate limiter for API endpoints (e.g., chat and upload).
Provides the dependency `rate_limit()`.

Two properties an attacker would otherwise exploit:
  • The client address comes from X-Forwarded-For only as far as the proxies we trust
    append to it (ANTAR_TRUSTED_PROXY_HOPS). The LEFTMOST entry is whatever the caller
    typed, so reading it let anyone rotate a fake IP per request and never be limited.
  • The bucket table is bounded (LRU). Unbounded, a spray of distinct addresses grows
    it until the process runs out of memory.
"""

import time
from collections import OrderedDict
from fastapi import Request, HTTPException

from app.core.settings import settings

_MAX_KEYS = 10_000

# In-memory store: { key: (tokens, last_refill_timestamp) }, least-recently-seen first
_buckets: "OrderedDict[str, tuple[float, float]]" = OrderedDict()


def check_rate_limit(ip: str, capacity: int = 60, refill_rate: float = 1.0) -> bool:
    """
    Check if the IP is within the rate limit.
    capacity: maximum burst tokens
    refill_rate: tokens added per second (e.g. 1.0 = 60 per minute)
    Returns True if allowed, False if rejected.
    """
    now = time.monotonic()

    if ip not in _buckets:
        _buckets[ip] = (capacity - 1.0, now)
        while len(_buckets) > _MAX_KEYS:
            _buckets.popitem(last=False)
        return True

    tokens, last_refill = _buckets[ip]
    _buckets.move_to_end(ip)

    # Refill tokens
    elapsed = now - last_refill
    tokens = min(capacity, tokens + elapsed * refill_rate)

    if tokens < 1.0:
        _buckets[ip] = (tokens, now)
        return False

    _buckets[ip] = (tokens - 1.0, now)
    return True


def client_ip(request: Request) -> str:
    """The address of the caller as seen by the nearest trusted proxy."""
    client = request.client
    ip = client.host if client else "127.0.0.1"
    hops = max(0, int(settings.ANTAR_TRUSTED_PROXY_HOPS))
    xff = request.headers.get("X-Forwarded-For")
    if hops and xff:
        chain = [p.strip() for p in xff.split(",") if p.strip()]
        if chain:
            # Each trusted proxy appends the address it received from; the entry `hops`
            # from the right is the one our outermost proxy vouched for.
            ip = chain[-hops] if len(chain) >= hops else chain[0]
    return ip[:64]


def rate_limit(capacity: int = 60, refill_rate: float = 1.0):
    """FastAPI Dependency for rate limiting."""
    def _dependency(request: Request):
        if not check_rate_limit(client_ip(request), capacity, refill_rate):
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")

    return _dependency
