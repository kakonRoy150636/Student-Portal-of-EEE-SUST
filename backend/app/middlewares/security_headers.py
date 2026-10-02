"""Defence-in-depth response headers for the API itself.

nginx is the primary place for these (see `frontend/nginx.conf`), because it
also serves the SPA and the static bundle. But the API is reachable directly
-- on its own port in development, and possibly behind a different proxy in a
real deployment -- so it must not rely on a front end it does not control.

`Strict-Transport-Security` is only emitted when `ENVIRONMENT=production`:
HSTS on a plain-HTTP dev server would pin a browser to https for localhost and
break the next local run. The non-transport headers are safe everywhere.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # The API returns JSON only. `nosniff` stops a browser from
        # reinterpreting a JSON error body as HTML, which is what turns a
        # reflected error message into script execution.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # No API response is ever meant to be framed or used as a document.
        response.headers.setdefault("X-Frame-Options", "DENY")
        # Do not leak the full request URL (which can contain identifiers or
        # resource ids) to third-party origins on navigation.
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        # Defence in depth for an API: nothing here should ever be embedded or
        # loaded as a script/style by another origin.
        #
        # The interactive docs are the one exception: Swagger UI ships its own
        # inline bootstrap script and loads its bundle from a CDN, so
        # `default-src 'none'` would produce a blank page. Docs are disabled in
        # production entirely (see app.main), so the relaxed policy below only
        # ever applies to a development server.
        if request.url.path.startswith(("/api/docs", "/redoc", "/docs/oauth2-redirect")):
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "frame-ancestors 'none'",
            )
        else:
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )

        if settings.ENVIRONMENT.lower() == "production":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        return response
