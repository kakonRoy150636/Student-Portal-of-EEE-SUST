"""Login throttling backed by Redis.

Two *independent* counters are used, and the larger delay wins:

- ``login:acct:<identifier-hash>`` -- failures against a single account.
- ``login:ip:<ip>`` -- failures from one address across *all* accounts.

Both are needed. A compound ``identifier+IP`` key cannot stop an attacker
spraying a single password across thousands of student identifiers from one
address, because every pair starts from a virgin counter and no individual
account ever accumulates failures. That is a credential-stuffing pattern,
and it is the common one.
"""

from __future__ import annotations

import asyncio
import hashlib

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import settings

# Thresholds are expressed in seconds of imposed delay, not in a failure
# count. A count-based ceiling was the first attempt and it was wrong: it made
# a *correct* password wait just as long as a wrong one after enough
# failures, so an attacker could lock any account they could name simply by
# failing N times for it. Succeeding must therefore be exempt from waiting.
#
# One schedule, two grace windows. The per-account window is small so a
# targeted brute force against one student ID starts paying immediately
# after a few mistypes. The per-IP window is larger because a campus NAT
# is one address shared by hundreds of students -- treating it like a
# single attacker would punish everyone behind it for the first few
# mistypes of the day. After the grace window the same exponential
# schedule applies, and the larger of the two delays wins.
BACKOFF_SCHEDULE = (1, 2, 4, 8, 16, 32, 64, 128, 256, 300, 300)
# Below this the delay is not worth the round trip and the user experience
# cost, so no sleep is imposed at all.
BACKOFF_FLOOR_SECONDS = 1

# First N failures impose no delay. A real user who mistypes a few times
# should not notice; a sprayer who burns through the grace window then pays
# the exponential schedule.
ACCOUNT_GRACE_FAILURES = 4
IP_GRACE_FAILURES = 20


# A clean login clears the per-account counter. The per-IP counter is left to
# decay on its own rather than being reset, so one attacker cannot reset their
# own spraying budget by periodically landing a correct password.
FAILURE_WINDOW_SECONDS = 900

_redis: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


def _account_key(identifier: str) -> str:
    # Hashed: raw identifiers and emails must not land in Redis keyspaces that
    # ops tooling routinely dumps, and this keeps keys bounded in length.
    digest = hashlib.sha256(identifier.strip().lower().encode("utf-8")).hexdigest()
    return f"login:acct:{digest}"


def _ip_key(ip: str) -> str:
    return f"login:ip:{ip}"


def _backoff_seconds(failures: int, grace: int) -> int:
    """Delay after ``failures`` failures, skipping the first ``grace``.

    ``grace`` is the number of free attempts. The schedule starts on the
    attempt *after* that, so a user who mistypes ``grace`` times waits 0s
    and only the next one pays ``BACKOFF_SCHEDULE[0]``.
    """
    charged = failures - grace
    if charged <= 0:
        return 0
    index = min(charged, len(BACKOFF_SCHEDULE)) - 1
    return BACKOFF_SCHEDULE[index]


async def check_login_allowed(identifier: str, ip: str, skip_wait: bool = False) -> int:
    """Return the delay owed by an attempt whose password is not yet known.

    Call this *before* verifying credentials to read the counters and pay any
    delay owed from earlier failures. It is deliberately NOT where a correct
    password gets exempted -- :func:`verify_attempt` is, after the password has
    actually been checked. Charging the wait twice would double every penalty.

    Fails *open* if Redis is unreachable: an availability outage in the
    throttle store must not become an outage in login itself.
    """
    if skip_wait:
        return 0

    try:
        client = _get_redis()
        acct_failures = int(await client.get(_account_key(identifier)) or 0)
        ip_failures = int(await client.get(_ip_key(ip)) or 0)
    except (RedisError, OSError, ValueError):
        return 0

    # Either counter alone can impose a wait, so the larger of the two wins.
    wait = max(
        _backoff_seconds(acct_failures, ACCOUNT_GRACE_FAILURES),
        _backoff_seconds(ip_failures, IP_GRACE_FAILURES),
    )
    if wait >= BACKOFF_FLOOR_SECONDS:
        # Sleep server-side rather than trusting the client to honour a
        # Retry-After, since a scripted attacker simply ignores it.
        await asyncio.sleep(wait)
    return wait


async def verify_attempt(identifier: str, password_ok: bool, ip: str) -> int:
    """Impose the throttle for a failed attempt and sleep out the penalty.

    Called *after* the password has been checked, so the wait is applied only
    to genuinely wrong credentials and never to a correct one. Returns the
    number of seconds slept.
    """
    if password_ok:
        await record_login_success(identifier)
        return 0

    await record_login_failure(identifier, ip)
    acct_failures, ip_failures = 1, 0
    try:
        client = _get_redis()
        acct_failures = int(await client.get(_account_key(identifier)) or 1)
        ip_failures = int(await client.get(_ip_key(ip)) or 0)
    except (RedisError, OSError, ValueError):
        # Fall back to no delay if Redis died between the increment and the
        # read; the next attempt will see the recorded counter.
        pass
    # Both counters must be consulted here, exactly as in
    # check_login_allowed. Reading only the account counter meant a spray --
    # one password tried across many identifiers from a single address --
    # incremented the IP counter but never paid for it, so the per-IP defence
    # did nothing at all. Taking the max closes that.
    wait = max(
        _backoff_seconds(acct_failures, ACCOUNT_GRACE_FAILURES),
        _backoff_seconds(ip_failures, IP_GRACE_FAILURES),
    )
    if wait >= BACKOFF_FLOOR_SECONDS:
        await asyncio.sleep(wait)
    return wait


async def record_login_failure(identifier: str, ip: str) -> None:
    """Increment both counters after a failed attempt."""
    try:
        client = _get_redis()
        pipe = client.pipeline()
        pipe.incr(_account_key(identifier))
        pipe.expire(_account_key(identifier), FAILURE_WINDOW_SECONDS)
        pipe.incr(_ip_key(ip))
        pipe.expire(_ip_key(ip), FAILURE_WINDOW_SECONDS)
        await pipe.execute()
    except (RedisError, OSError):
        return


async def record_login_success(identifier: str) -> None:
    """Clear the per-account counter after a successful login."""
    try:
        await _get_redis().delete(_account_key(identifier))
    except (RedisError, OSError):
        return
