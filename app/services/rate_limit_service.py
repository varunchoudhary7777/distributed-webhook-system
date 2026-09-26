from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.config import settings
from app.infrastructure.redis import redis_client

RATE_LIMIT_SCRIPT = """
local current = redis.call("INCR, KEYS[1])

if current == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end

local ttl = redis.call("TTL", KEYS[1])

return {current, ttl}
"""


@dataclass
class RateLimitResult:
    allowed: bool
    current: int
    limit: int
    remaining: int
    reset_after: int

async def check_rate_limit(
    identifier: str,
) -> RateLimitResult:

    key = f"rate_limit:{identifier}"

    result = await redis_client.eval(
        RATE_LIMIT_SCRIPT,
        1,
        key,
        settings.rate_limit_window_seconds,
    )

    current = int(result[0])
    ttl = int(result[1])

    limit = settings.rate_limit_requests

    remaining = max(0, limit - current)

    if current > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many requests",
                "limit": limit,
                "remaining": 0,
                "retry_after": max(ttl,0),
            },
            headers={
                "Retry-After": str(max(ttl, 0)),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    return RateLimitResult(
        allowed=True,
        current=current,
        limit=limit,
        remaining=remaining,
        reset_after=max(ttl, 0),
    )