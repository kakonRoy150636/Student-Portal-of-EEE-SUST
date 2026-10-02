"""Google Gemini access over the REST API.

Why REST and not `google-generativeai`: the SDK is synchronous, so every call
would block the event loop for the length of an LLM round trip (seconds).
httpx is already a dependency and gives a native async client.

Everything here is *optional at runtime*. A deployment without
``GEMINI_API_KEY`` still boots and still answers questions -- the RAG service
falls back to extractive answers from retrieved documents (see
``app/services/ai_rag_service.py``), which is the honest behaviour. The
previous implementation returned a hardcoded sentence that only *looked* like
a model answer, which is worse than saying nothing.
"""

from __future__ import annotations

import structlog
import httpx

from app.core.config import settings

logger = structlog.get_logger(__name__)

_API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
_TIMEOUT = httpx.Timeout(20.0, connect=5.0)


def is_configured() -> bool:
    """Whether a Gemini key is present, i.e. generation/embedding can be tried."""
    return bool((settings.GEMINI_API_KEY or "").strip())


async def embed_text(text: str) -> list[float] | None:
    """Embed a chunk of text, or return None when unavailable.

    Returning None rather than raising keeps the caller's control flow simple:
    ingestion stores the chunk unembedded (the column is nullable precisely for
    this) and retrieval falls back to full-text search.
    """
    if not is_configured() or not text.strip():
        return None
    url = f"{_API_ROOT}/models/{settings.GEMINI_EMBEDDING_MODEL}:embedContent"
    payload = {"content": {"parts": [{"text": text[:8000]}]}}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                url, json=payload, headers={"x-goog-api-key": settings.GEMINI_API_KEY}
            )
            response.raise_for_status()
            values = response.json()["embedding"]["values"]
        if len(values) != settings.EMBEDDING_DIM:
            # A model change with a different width would silently break the
            # pgvector column (vector(768)); refuse rather than store garbage.
            logger.warning(
                "embedding_dimension_mismatch",
                expected=settings.EMBEDDING_DIM,
                received=len(values),
            )
            return None
        return values
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        logger.warning("embedding_failed", error=str(exc))
        return None


async def generate_text(prompt: str, *, system: str | None = None) -> str | None:
    """Ask Gemini to write an answer. Returns None on any failure."""
    if not is_configured() or not prompt.strip():
        return None
    url = f"{_API_ROOT}/models/{settings.GEMINI_MODEL}:generateContent"
    payload: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt[:16000]}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system[:4000]}]}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                url, json=payload, headers={"x-goog-api-key": settings.GEMINI_API_KEY}
            )
            response.raise_for_status()
            candidates = response.json().get("candidates") or []
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts).strip()
        return text or None
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        logger.warning("generation_failed", error=str(exc))
        return None
