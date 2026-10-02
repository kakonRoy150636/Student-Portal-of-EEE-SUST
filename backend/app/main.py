from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.bootstrap import ensure_bootstrap_admin
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import setup_logging
from app.middlewares.correlation_id import CorrelationIdMiddleware
from app.middlewares.error_handler import register_exception_handlers
from app.middlewares.security_headers import SecurityHeadersMiddleware
from app.api.v1.router import api_router

# Configured at import time, not only in the lifespan: anything logged before
# startup (a migration error, an import failure) would otherwise be rendered by
# structlog's *default* console renderer -- which is rich-formatted, colourised
# and, for a deep async traceback, seconds of CPU on the process that is trying
# to report a failure.
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Create the environment-provided administrator on first start, if any.
    # No-ops when the variables are unset or an admin already exists.
    await ensure_bootstrap_admin(AsyncSessionLocal)
    yield

app = FastAPI(
    title="SUST EEE Smart Student Portal API",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Added last so it is the outermost layer: every response -- including CORS
# preflights that short-circuit inside the CORS middleware -- leaves with the
# hardening headers attached.
app.add_middleware(SecurityHeadersMiddleware)

register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SUST EEE Portal API"}
