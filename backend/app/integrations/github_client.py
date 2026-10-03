import hmac
import hashlib
import re

def verify_github_signature(payload_body: bytes, secret: str, signature_header: str) -> bool:
    """Validate GitHub's HMAC signature without allowing malformed input to 500."""
    if not secret or not signature_header:
        return False
    try:
        hash_type, signature = signature_header.split('=', 1)
    except ValueError:
        return False
    if hash_type != "sha256" or not re.fullmatch(r"[0-9a-fA-F]{64}", signature):
        return False
    mac = hmac.new(secret.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature.lower())
