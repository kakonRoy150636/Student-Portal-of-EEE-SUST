from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev_secret_key_sust_eee_smart_student_portal_256bit"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/sust_eee_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    REDIS_URL: str = "redis://redis:6379/0"
    # Peer addresses permitted to speak for the client via X-Forwarded-For.
    # Empty by default, which is correct while the API port is reached
    # directly: XFF is client-controlled, so trusting it unconditionally would
    # let an attacker mint a fresh throttle bucket per request and bypass the
    # per-IP counter. Populate this when a reverse proxy fronts the API.
    TRUSTED_PROXIES: List[str] = []
    # Parseable so a real deployment can supply its own origins as
    # CORS_ORIGINS='["https://portal.sust.edu"]' without a code change.
    # Defaults remain the local dev servers.
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ]

    # First-boot super_admin. Leaving these unset is valid and simply skips
    # bootstrap (local development). When set, they are consumed once -- the
    # password is hashed and never read again, so it can be rotated in the
    # environment without touching a committed file. See core/bootstrap.py.
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""
    BOOTSTRAP_ADMIN_IDENTIFIER: str = "admin"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    AI_DAILY_USER_QUOTA: int = Field(default=20, ge=1)
    AI_GLOBAL_DAILY_CAP_MICRO_USD: int = Field(default=1_000_000, ge=1)
    # Conservative price ceilings in micro-USD per million tokens, not a
    # statement of Google's current pricing. Operators may raise these ceilings.
    AI_INPUT_MICRO_USD_PER_MILLION: int = Field(default=1_000_000, ge=1)
    AI_OUTPUT_MICRO_USD_PER_MILLION: int = Field(default=5_000_000, ge=1)
    AI_EMBED_MICRO_USD_PER_MILLION: int = Field(default=150_000, ge=1)
    AI_MAX_OUTPUT_TOKENS: int = Field(default=768, ge=64, le=2048)
    AI_RRF_LEXICAL_WEIGHT: float = Field(default=1.0, ge=0)
    AI_RRF_VECTOR_WEIGHT: float = Field(default=1.0, ge=0)
    AI_RRF_K: int = Field(default=60, ge=1)
    AI_RETRIEVAL_TOP_K: int = Field(default=5, ge=1, le=8)
    AI_MIN_LEXICAL_COVERAGE: float = Field(default=0.6, ge=0, le=1)
    AI_MIN_VECTOR_SIMILARITY: float = Field(default=0.8, ge=0, le=1)
    GITHUB_WEBHOOK_SECRET: str = ""
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-service-account.json"

    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_PUBLIC_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "sust-eee-resources"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# --- production safety net -------------------------------------------------
# The default SECRET_KEY is committed to the repository, so a deployment that
# sets ENVIRONMENT=production without supplying its own key would sign JWTs
# with a value every reader of the source can forge. Refusing to start is
# far better than shipping a forgeable token to production.
_WEAK_SECRET_KEYS = {
    "dev_secret_key_change_in_production_sust_eee_256bit",
    "dev_secret_key_sust_eee_smart_student_portal_256bit",
    "changeme",
    "secret",
    "supersecret",
}

if settings.ENVIRONMENT.lower() == "production":
    from sqlalchemy.engine import make_url

    required = {"SECRET_KEY", "DATABASE_URL", "S3_ACCESS_KEY", "S3_SECRET_KEY"}
    if required - settings.model_fields_set:
        raise RuntimeError("Production requires explicit SECRET_KEY, DATABASE_URL and S3 credentials.")
    database_password = make_url(settings.DATABASE_URL).password
    if not database_password or database_password.lower() in {"postgres", "password", "changeme"}:
        raise RuntimeError("Production DATABASE_URL requires a non-default password.")
    if not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY or settings.S3_SECRET_KEY.lower() in {"minioadmin", "password", "changeme"}:
        raise RuntimeError("Production requires non-default S3 credentials.")
    if settings.SECRET_KEY in _WEAK_SECRET_KEYS or len(settings.SECRET_KEY) < 32:
        raise RuntimeError(
            "SECRET_KEY must be set to a unique value of at least 32 characters "
            "when ENVIRONMENT=production. Refusing to start with a weak key."
        )
    insecure_origins = [
        origin
        for origin in settings.CORS_ORIGINS
        if not origin.startswith("https://") or origin == "https://"
    ]
    if insecure_origins:
        raise RuntimeError(
            f"CORS_ORIGINS must use https in production; found {insecure_origins}."
        )
