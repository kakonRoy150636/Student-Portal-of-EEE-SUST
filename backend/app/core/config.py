from typing import List
from pydantic_settings import BaseSettings

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

    GEMINI_API_KEY: str = ""
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
    "dev_secret_key_sust_eee_smart_student_portal_256bit",
    "changeme",
    "secret",
    "supersecret",
}

if settings.ENVIRONMENT.lower() == "production":
    if settings.SECRET_KEY in _WEAK_SECRET_KEYS or len(settings.SECRET_KEY) < 32:
        raise RuntimeError(
            "SECRET_KEY must be set to a unique value of at least 32 characters "
            "when ENVIRONMENT=production. Refusing to start with a weak key."
        )
    insecure_origins = [
        origin
        for origin in settings.CORS_ORIGINS
        if origin.startswith("http://") and not origin.startswith("http://localhost")
    ]
    if insecure_origins:
        raise RuntimeError(
            f"CORS_ORIGINS must use https in production; found {insecure_origins}."
        )
