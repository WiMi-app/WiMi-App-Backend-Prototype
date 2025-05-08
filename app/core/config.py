from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from supabase import create_client, Client
import os
class Settings(BaseSettings):
    # ─── App Metadata ────────────────────────────────────────────────────────
    APP_NAME: str = Field("WiMi", env="APP_NAME")
    APP_VERSION: str = Field("0.1.0", env="APP_VERSION")
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    PORT: int = Field(8000, env="PORT")
    API_V1_STR: str = Field("/api/v0", env="API_V1_STR")

    # ─── Supabase ─────────────────────────────────────────────────────────────
    SUPABASE_URL: str = Field(os.getenv("SUPABASE_URL"), env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(os.getenv("SUPABASE_KEY"), env="SUPABASE_KEY")

    # ─── OpenAI ─────────────────────────────────────────────────────────────
    OPENAI_KEY: str = Field(os.getenv("OPENAI_API_KEY"), env="OPENAI_API_KEY")

    # ─── JWT / Auth ───────────────────────────────────────────────────────────
    JWT_SECRET: str = Field(os.getenv("SECRET_KEY"), env="SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        60, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # ─── CORS ─────────────────────────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: str = Field(os.getenv("BACKEND_CORS_ORIGINS"), env="BACKEND_CORS_ORIGINS")

    # ─── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = Field(os.getenv("LOG_LEVEL"), env="LOG_LEVEL")

    # ─── Pydantic-Settings Config ─────────────────────────────────────────────
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_cors_origins(self) -> list[str]:
        """
        Helper to turn a CSV string into a list of origins.
        """
        if not self.BACKEND_CORS_ORIGINS:
            return []
        return [u.strip() for u in self.BACKEND_CORS_ORIGINS.split(",") if u.strip()]

# instantiate
settings = Settings()

# Initialize Supabase client
supabase: Client = create_client(
    supabase_url=str(settings.SUPABASE_URL),
    supabase_key=settings.SUPABASE_KEY,
)
