"""Application configuration using pydantic-settings."""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Application
    APP_NAME: str = "Cake Shop AI API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Frontend URL (used for password reset redirect)
    FRONTEND_URL: str = "http://localhost:3000"

    # CORS — allow frontend tren cac port thong dung khi dev (3000, 3001, 3002)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ]

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Groq API (Free)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # JWT
    JWT_SECRET_KEY: str = "change-this-to-a-secure-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    def __init__(self, **values):
        super().__init__(**values)
        import os
        frontend_port = os.environ.get("FRONTEND_PORT")
        if frontend_port:
            for host in ["localhost", "127.0.0.1"]:
                origin = f"http://{host}:{frontend_port}"
                if origin not in self.CORS_ORIGINS:
                    self.CORS_ORIGINS = list(self.CORS_ORIGINS) + [origin]


settings = Settings()
