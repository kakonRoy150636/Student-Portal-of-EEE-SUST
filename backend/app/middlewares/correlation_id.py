import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.correlation_id = cid
        response = await call_next(request)
        response.headers["X-Request-ID"] = cid
        return response
