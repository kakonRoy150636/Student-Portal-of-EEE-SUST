"""Atomic Redis fixed-window request budgets, shared by all API replicas."""
import hashlib
import logging

from fastapi import HTTPException
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.rate_limit import _get_redis

logger = logging.getLogger(__name__)
WINDOW_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
local ttl = redis.call('TTL', KEYS[1])
if ttl < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
    ttl = tonumber(ARGV[1])
end
return {count, ttl}
"""


async def enforce_request_limit(scope: str, identity: str, maximum: int, window: int = 60):
    digest = hashlib.sha256(identity.encode()).hexdigest()
    key = f"portal:limit:{scope}:{digest}"
    try:
        count, ttl = await _get_redis().eval(WINDOW_SCRIPT, 1, key, window)
    except (RedisError, OSError, ValueError):
        logger.warning("Rate-limit store unavailable for %s", scope)
        if settings.ENVIRONMENT.lower() == "production":
            raise HTTPException(503, "Request limiting temporarily unavailable.", headers={"Retry-After": "5"})
        return
    if int(count) > maximum:
        raise HTTPException(429, "Too many requests. Please try again later.", headers={"Retry-After": str(max(1, int(ttl)))})
