import os
from typing import List, Union, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Vendor Onboarding Platform"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "insecure-dev-secret-key-please-change-in-production-random-bytes"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database
    # Defaults to SQLite for local development when PostgreSQL server is not locally active,
    # or a PostgreSQL URI (e.g. Supabase, local PostgreSQL) via environment variable.
    DATABASE_URL: str = "sqlite:///./vendor_onboarding.db"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Storage
    STORAGE_BACKEND: str = "local"  # "local" or "supabase"
    STORAGE_LOCAL_DIR: str = "./storage_uploads"
    MAX_FILE_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    ALLOWED_MIME_TYPES: List[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
    ]

    # AI Integration (Optional)
    GEMINI_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_secret(self):
        if self.ENVIRONMENT.lower() == "production" and (
            len(self.SECRET_KEY) < 32
            or "insecure-dev" in self.SECRET_KEY.lower()
            or "change-in-production" in self.SECRET_KEY.lower()
        ):
            raise ValueError("SECRET_KEY must be a unique secret of at least 32 characters in production")
        return self


settings = Settings()
