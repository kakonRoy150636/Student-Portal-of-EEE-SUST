import hashlib
import hmac

from app.integrations.github_client import verify_github_signature


def test_github_signature_rejects_malformed_headers():
    assert not verify_github_signature(b"{}", "secret", "not-a-signature")
    assert not verify_github_signature(b"{}", "secret", "sha1=abc")
    assert not verify_github_signature(b"{}", "secret", "sha256=")


def test_github_signature_accepts_valid_sha256_header():
    body = b'{"action":"push"}'
    digest = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    assert verify_github_signature(body, "secret", f"sha256={digest}")
    assert not verify_github_signature(body + b" ", "secret", f"sha256={digest}")
