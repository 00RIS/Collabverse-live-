
"""
app/core/config.py

Central configuration for the CollabVerse backend.
Loads environment variables from .env.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Optional Google Cloud Storage bucket for persistent user uploads.
    # When empty, uploads are stored on the local filesystem for development.
    GCS_BUCKET_NAME: str = ""
    # Optional service-account JSON for hosting providers without Google ADC.
    GCS_SERVICE_ACCOUNT_JSON: str = ""
    # Optional Cloudinary credentials; when all are set, Cloudinary is preferred.
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    UPLOADS_DIR: str = ""

    # JWT authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = (
        "http://127.0.0.1:8000/api/v1/auth/google/callback"
    )
    FRONTEND_URL: str = "http://127.0.0.1:5173"
    CORS_ORIGINS: str = ""

    # Gemini AI
    GEMINI_API_KEY: str

    # Application
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
