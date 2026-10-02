"""Async wrappers around the (CPU-bound) bcrypt primitives.

bcrypt is a C extension, but ``bcrypt.hashpw``/``checkpw`` are *synchronous*
calls: at the default cost factor each one burns 150-300 ms of CPU. Running
them directly inside ``async def`` code blocks the event loop for that whole
window, so every other coroutine on the worker -- health checks, refreshes,
the dashboard of every logged-in user -- waits behind a single login.

That is not a theoretical concern: the login throttle deliberately *sleeps*
after a failed password, and while ``asyncio.sleep`` yields, a blocking
bcrypt call immediately before it does not. A burst of concurrent login or
registration attempts therefore turns into a cheap availability attack.

AnyIO ships with FastAPI/Starlette, so the fix is to hand the hash to the
default thread pool, where the GIL is released for the duration of the C
call. The sync functions in :mod:`app.core.security` stay available for
tests and for non-request code.
"""

from __future__ import annotations

from anyio import to_thread

from app.core.security import get_password_hash, verify_password

# A fixed bcrypt hash of a random throwaway value. Compared against when the
# supplied account does not exist, so a *missing* user costs the same wall
# time as a *wrong password*. Without this, `bool(user) and verify_password(...)`
# short-circuits and the uniform "invalid identifier or password" message is
# undermined by response timing -- an attacker can still tell which
# identifiers are real.
_DUMMY_HASH = "$2b$12$f4SXyJt9Y2n2H2qh/QkzIOh4krXvTj/2K59JYzYSqId78W8twY28C"


async def hash_password(password: str) -> str:
    """Hash a password without blocking the event loop."""
    return await to_thread.run_sync(get_password_hash, password)


async def verify_password_async(plain_password: str, hashed_password: str | None) -> bool:
    """Verify a password, burning constant-ish time when the account is absent."""
    candidate = hashed_password or _DUMMY_HASH
    ok = await to_thread.run_sync(verify_password, plain_password, candidate)
    # Always False when there was no stored hash, even in the (impossible)
    # case the dummy hash accidentally matched.
    return bool(hashed_password) and ok
