from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import structlog

from app.core.exceptions import DomainException

logger = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainException)
    async def domain_handler(req: Request, exc: DomainException):
        body = {"error": exc.message}
        if getattr(exc, "code", None):
            body["code"] = exc.code
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(IntegrityError)
    async def integrity_handler(req: Request, exc: IntegrityError):
        """Turn a database constraint violation into a 409, not a 500.

        A duplicate key, a missing foreign key or a GiST exclusion conflict is
        a *client* problem. Letting the driver exception escape produced an
        opaque 500 (and, before this handler, a stack trace in the logs with
        no request context). The driver message is deliberately not echoed --
        it names tables and columns -- so the response stays generic while the
        log keeps the detail.
        """
        logger.warning(
            "db_integrity_error",
            path=req.url.path,
            method=req.method,
            constraint=getattr(getattr(exc, "orig", None), "constraint_name", None),
        )
        return JSONResponse(
            status_code=409,
            content={"error": "The request conflicts with existing data."},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_handler(req: Request, exc: SQLAlchemyError):
        logger.error("db_error", path=req.url.path, error=type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"error": "The database is temporarily unavailable."},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(req: Request, exc: Exception):
        """Last-resort handler: log the traceback, return a clean body.

        Without this, Starlette's default 500 response is a bare text body and
        the traceback goes to stderr with no correlation id, which made
        production failures hard to tie back to a request.
        """
        logger.exception("unhandled_exception", path=req.url.path, method=req.method)
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred."},
        )
