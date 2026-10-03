import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.bootstrap import ensure_bootstrap_admin
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import setup_logging
from app.middlewares.correlation_id import CorrelationIdMiddleware
from app.middlewares.error_handler import register_exception_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Create the first super_admin from BOOTSTRAP_ADMIN_* if configured. This
    # replaced a super_admin row whose bcrypt hash was committed in seed.sql.
    # A failure here must not take the API down: an operator who has not set
    # the variables should still get a running (read-only) portal rather than
    # a crash loop. The error is logged loudly instead.
    try:
        async with AsyncSessionLocal() as session:
            await ensure_bootstrap_admin(session)
    except Exception:
        logger.exception("Bootstrap admin step failed; continuing startup.")
    yield


app = FastAPI(
    title="SUST EEE Smart Student Portal API",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if settings.ENVIRONMENT == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SUST EEE Portal API"}
