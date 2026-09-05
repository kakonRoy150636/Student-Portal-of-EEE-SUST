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
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    GEMINI_API_KEY: str = ""
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-service-account.json"

    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "sust-eee-resources"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
