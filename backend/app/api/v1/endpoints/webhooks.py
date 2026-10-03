import json

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.integrations.github_client import verify_github_signature

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
MAX_WEBHOOK_BYTES = 1024 * 1024


@router.post("/github")
async def github_webhook(request: Request):
    if not settings.GITHUB_WEBHOOK_SECRET:
        raise HTTPException(503, "GitHub webhook is not configured.")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_WEBHOOK_BYTES:
            raise HTTPException(413, "Webhook payload is too large.")
        body.extend(chunk)
    if not verify_github_signature(bytes(body), settings.GITHUB_WEBHOOK_SECRET, request.headers.get("x-hub-signature-256", "")):
        raise HTTPException(401, "Invalid webhook signature.")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "Invalid JSON payload.")
    if not isinstance(payload, dict):
        raise HTTPException(400, "Expected a JSON object.")
    if request.headers.get("x-github-event") == "ping":
        return {"status": "verified", "event": "ping"}
    # The repo has no project synchronization consumer. Acknowledge honestly;
    # no database writes/jobs means replay cannot repeat business side effects.
    return {"status": "ignored", "reason": "Event processing is not implemented."}
