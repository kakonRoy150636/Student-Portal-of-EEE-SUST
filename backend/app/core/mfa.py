"""TOTP second factor and one-time recovery codes.

Kept apart from the auth service so the crypto-ish parts are unit-testable
without a database: a secret generator, an otpauth:// URI for authenticator
apps, a verifier with a small clock-skew window, and recovery codes that are
stored only as SHA-256 hashes.
"""

from __future__ import annotations

import hashlib
import secrets

import pyotp

from app.core.config import settings

RECOVERY_CODE_COUNT = 10


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, account_name: str) -> str:
    """otpauth:// URI an authenticator app can scan or read."""
    return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=settings.MFA_ISSUER)


def verify_totp(secret: str, code: str) -> bool:
    """Verify a 6-digit code, tolerating one step of clock skew either way.

    ``valid_window=1`` accepts the previous/next 30-second step. That is the
    usual tolerance for phone clocks that are slightly off, and it triples the
    guessing surface from 1-in-a-million to 3-in-a-million per attempt -- which
    the per-account login throttle, not the code length, is what makes safe.
    """
    if not secret or not code or not code.strip().isdigit():
        return False
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=settings.MFA_VALID_WINDOW)


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    """Human-transcribable one-time codes, e.g. ``4f2a-91c7``."""
    codes: list[str] = []
    while len(codes) < count:
        raw = secrets.token_hex(4)  # 8 hex chars
        code = f"{raw[:4]}-{raw[4:]}"
        if code not in codes:
            codes.append(code)
    return codes


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.strip().lower().encode("utf-8")).hexdigest()


def recovery_codes_match(stored_hashes: list[str] | None, code: str) -> str | None:
    """Return the matching hash (so the caller can consume it), else None."""
    if not stored_hashes:
        return None
    candidate = hash_recovery_code(code)
    return candidate if candidate in stored_hashes else None
