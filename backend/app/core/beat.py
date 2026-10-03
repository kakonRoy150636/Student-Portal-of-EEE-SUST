"""A Redis-leased, fail-closed Celery Beat scheduler.

The 30-second lease exceeds the five-second tick interval, a ten-second hard
tick deadline, and Redis socket operations (two seconds, no publish retries).
Ownership is checked before every tick and immediately before publication. A Redis
outage, unsupported broker, or uncertain ownership suppresses publication.

A lease is not broker-side fencing: a process/VM pause after the last ownership
check, Redis failover losing the lock, or a blocking custom task publisher can
outlive the TTL. Keep Beat on the bounded Redis transport below, retain worker
idempotency, and use one deployment replica. The hard deadline requires Unix
main-thread Beat; unsupported execution contexts fail closed. The lease protects
against accidental concurrent Beat instances under normal bounded operation.
"""

import signal
from contextlib import contextmanager
from copy import copy
from threading import current_thread, main_thread
from time import monotonic
from uuid import uuid4
from typing import Any

from celery.beat import PersistentScheduler
from kombu.exceptions import OperationalError
from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

from app.core.config import settings

LOCK_KEY = "portal:celery-beat"
LEASE_TTL_SECONDS = 30
POLL_INTERVAL_SECONDS = 5
SOCKET_TIMEOUT_SECONDS = 2
MAX_TICK_SECONDS = 10

_RENEW = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('expire', KEYS[1], ARGV[2])
end
return 0
"""
_RELEASE = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


class _TickDeadlineExceeded(BaseException):
    """Escape Celery's broad publication exception handlers on lease risk."""


@contextmanager
def _tick_deadline(seconds):
    # Per-socket timeouts do not bound the total number of broker operations,
    # DNS resolution, signal hooks, or a custom task's apply_async. Interrupt
    # the entire tick as well. Do not replace another component's active timer.
    if (
        seconds <= 0
        or current_thread() is not main_thread()
        or not hasattr(signal, "setitimer")
        or signal.getitimer(signal.ITIMER_REAL)[0]
    ):
        yield False
        return

    def expired(signum, frame):
        raise _TickDeadlineExceeded()

    previous = signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield True
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class RedisLease:
    """Testable ownership helper; ambiguous Redis replies always fail closed."""

    def __init__(self, client=None):
        self.client = client if client is not None else Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=SOCKET_TIMEOUT_SECONDS,
            socket_timeout=SOCKET_TIMEOUT_SECONDS,
            retry_on_timeout=False,
            retry=Retry(NoBackoff(), 0),
        )
        self.owner = uuid4().hex
        self.owned = False
        self.deadline = 0.0

    def acquire_or_renew(self) -> bool:
        try:
            if not self.owned:
                self.owned = bool(self.client.set(LOCK_KEY, self.owner, nx=True, ex=LEASE_TTL_SECONDS))
                if not self.owned:
                    return False
            return self.renew()
        except (RedisError, OSError):
            self.owned = False
            self.deadline = 0.0
            return False

    def renew(self) -> bool:
        started = monotonic()
        try:
            self.owned = bool(self.client.eval(_RENEW, 1, LOCK_KEY, self.owner, LEASE_TTL_SECONDS))
        except (RedisError, OSError):
            self.owned = False
        # Count response latency against the lease rather than overestimating it.
        self.deadline = started + LEASE_TTL_SECONDS if self.owned else 0.0
        return self.owned and monotonic() < self.deadline - POLL_INTERVAL_SECONDS

    def release(self) -> None:
        try:
            self.client.eval(_RELEASE, 1, LOCK_KEY, self.owner)
        except (RedisError, OSError):
            pass  # Expiry releases an unreachable lease; never delete blindly.
        finally:
            self.owned = False
            self.deadline = 0.0


class SingletonScheduler(PersistentScheduler):
    max_interval = POLL_INTERVAL_SECONDS

    def __init__(self, app, *args, lease=None, **kwargs):
        self._store: Any = None
        self.lease = lease if lease is not None else RedisLease()
        self._schedule_ready = False
        interval = kwargs.get("max_interval") or app.conf.beat_max_loop_interval or POLL_INTERVAL_SECONDS
        kwargs["max_interval"] = min(interval, POLL_INTERVAL_SECONDS)
        # These settings are local to the Beat process. Do not allow a network
        # reconnect/backoff loop to publish after lease ownership has expired.
        app.conf.broker_connection_timeout = SOCKET_TIMEOUT_SECONDS
        app.conf.broker_connection_max_retries = 0
        app.conf.task_publish_retry = False
        app.conf.broker_transport_options = {
            **(app.conf.broker_transport_options or {}),
            "socket_connect_timeout": SOCKET_TIMEOUT_SECONDS,
            "socket_timeout": SOCKET_TIMEOUT_SECONDS,
            "retry_on_timeout": False,
            "max_retries": 0,
        }
        super().__init__(app, *args, **kwargs)

    def setup_schedule(self):
        # A standby must not open/reset the owner's shelve file at startup.
        # Real setup is deferred until this instance has the lease.
        pass

    def _destroy_open_corrupted_schedule(self, exc):
        # Celery normally unlinks an unopenable DB, including a DB locked by a
        # paused previous owner. Fail closed instead of damaging that owner's DB.
        raise RuntimeError("Beat schedule database is unavailable; publication stopped") from None

    def _ensure_connected(self):
        return self.connection.ensure_connection(max_retries=0, timeout=SOCKET_TIMEOUT_SECONDS)

    def tick(self, *args, **kwargs):
        if not self.lease.acquire_or_renew():
            return self.max_interval
        # Other transports do not have the socket bounds configured above.
        if self.connection.transport.driver_type != "redis":
            self.lease.release()
            return self.max_interval
        if not self._schedule_ready:
            super().setup_schedule()
            self._schedule_ready = True
            if not self.lease.renew():
                return self.max_interval
        budget = min(MAX_TICK_SECONDS, self.lease.deadline - monotonic() - POLL_INTERVAL_SECONDS)
        try:
            with _tick_deadline(budget) as bounded:
                if bounded:
                    return min(super().tick(*args, **kwargs), self.max_interval)
        except (_TickDeadlineExceeded, RedisError, OSError, OperationalError):
            # Celery advances the entry before attempting publication; do not
            # retry an uncertain publish. Rebuild the heap on the next tick.
            self._heap = None
        return self.max_interval

    def apply_async(self, entry, producer=None, advance=True, **kwargs):
        # Producer construction and schedule calculation may take time. Recheck
        # here, after that work, rather than trusting the check at tick start.
        if not self.lease.renew():
            return None
        bounded_entry = copy(entry)
        bounded_entry.options = {**entry.options, "retry": False}
        return super().apply_async(bounded_entry, producer=producer, advance=advance, **kwargs)

    def close(self):
        try:
            if self._store is not None:
                super().close()
                self._store = None
        finally:
            self.lease.release()
