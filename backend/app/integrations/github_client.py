import hmac
import hashlib

def verify_github_signature(payload_body: bytes, secret: str, signature_header: str) -> bool:
    if not signature_header:
        return False
    hash_type, signature = signature_header.split('=')
    mac = hmac.new(secret.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature)
