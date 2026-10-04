"""Atomic daily request quotas and conservative cost reservations in Redis."""
import hashlib
import uuid
from typing import Any
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.rate_limit import _get_redis

DHAKA = ZoneInfo("Asia/Dhaka")
ADMIT = """
local count = tonumber(redis.call('GET', KEYS[1]) or '0')
local spent = tonumber(redis.call('GET', KEYS[2]) or '0')
local held = tonumber(redis.call('GET', KEYS[3]) or '0')
if tonumber(ARGV[1]) > 0 and count >= tonumber(ARGV[1]) then return {-1, count} end
if spent + held + tonumber(ARGV[2]) > tonumber(ARGV[3]) then return {-2, count} end
if redis.call('EXISTS', KEYS[4]) == 1 then return {-3, count} end
redis.call('INCR', KEYS[1])
redis.call('INCRBY', KEYS[3], ARGV[2])
redis.call('SET', KEYS[4], ARGV[2], 'EX', ARGV[4])
redis.call('EXPIRE', KEYS[1], ARGV[4])
redis.call('EXPIRE', KEYS[3], ARGV[4])
return {1, count + 1}
"""
SETTLE = """
local reserved = redis.call('GET', KEYS[1])
if not reserved then return 0 end
local cost = tonumber(ARGV[1])
if cost < 0 or cost > tonumber(reserved) then return -1 end
redis.call('DECRBY', KEYS[2], reserved)
redis.call('INCRBY', KEYS[3], cost)
redis.call('EXPIRE', KEYS[3], ARGV[2])
redis.call('DEL', KEYS[1])
return 1
"""


def daily_window(now=None):
    local = (now or datetime.now(timezone.utc)).astimezone(DHAKA)
    midnight = datetime.combine(local.date() + timedelta(days=1), datetime.min.time(), tzinfo=DHAKA)
    seconds = max(1, int((midnight - local).total_seconds()))
    return local.date().isoformat(), seconds


def token_cost(tokens: int, rate: int) -> int:
    return (tokens * rate + 999_999) // 1_000_000


@dataclass
class Reservation:
    store: Any
    day: str
    id: str
    reserved: int
    remaining: int
    ttl: int

    async def settle(self, cost: int):
        prefix = f"portal:{{ai-budget}}:{self.day}"
        try:
            result = await self.store.eval(SETTLE, 3, f"{prefix}:lease:{self.id}",
                                          f"{prefix}:held", f"{prefix}:spent", cost, self.ttl)
            if result == -1:
                raise ValueError("Accounting bound exceeded")
        except (RedisError, OSError, ValueError):
            # Unknown/failed accounting stays fully reserved (fail closed).
            raise HTTPException(503, "AI cost accounting is temporarily unavailable") from None


async def reserve_ai(user_id, maximum_cost: int, *, now=None, store=None, enforce_user_quota=True) -> Reservation:
    day, retry_after = daily_window(now)
    ttl = retry_after + 86400
    identity = hashlib.sha256(str(user_id).encode()).hexdigest()
    ident = uuid.uuid4().hex
    prefix = f"portal:{{ai-budget}}:{day}"
    store = store if store is not None else _get_redis()
    try:
        status, count = await store.eval(ADMIT, 4, f"{prefix}:user:{identity}", f"{prefix}:spent",
                                        f"{prefix}:held", f"{prefix}:lease:{ident}",
                                        settings.AI_DAILY_USER_QUOTA if enforce_user_quota else 0, maximum_cost,
                                        settings.AI_GLOBAL_DAILY_CAP_MICRO_USD, ttl)
    except (RedisError, OSError, ValueError, TypeError):
        raise HTTPException(503, "AI usage accounting is temporarily unavailable", headers={"Retry-After": "5"}) from None
    if status in (-1, -2):
        detail = "Daily AI query quota exhausted" if status == -1 else "Daily AI cost cap reached"
        raise HTTPException(429, detail, headers={"Retry-After": str(retry_after)})
    if status != 1:
        raise HTTPException(503, "AI usage accounting is temporarily unavailable")
    return Reservation(store, day, ident, maximum_cost, max(0, settings.AI_DAILY_USER_QUOTA - int(count)), ttl)
