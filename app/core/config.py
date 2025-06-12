import os

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings
from supabase import Client, create_client


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables with fallbacks.
    
    Settings are loaded from environment variables, .env file, or defaults defined here.
    Each setting has a descriptive Field with env parameter that maps to the corresponding
    environment variable name.
    """
    # ─── App Metadata ────────────────────────────────────────────────────────
    APP_NAME: str = Field("WiMi", env="APP_NAME")
    APP_VERSION: str = Field("0.1.0", env="APP_VERSION")
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    PORT: int = Field(8080, env="PORT")
    API_V1_STR: str = Field("/api/v0", env="API_V1_STR")

    # ─── Supabase ─────────────────────────────────────────────────────────────
    SUPABASE_URL: str = Field(os.getenv("SUPABASE_URL"), env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(os.getenv("SUPABASE_KEY"), env="SUPABASE_KEY")

    # ─── OpenAI ─────────────────────────────────────────────────────────────
    OPENAI_KEY: str = Field(os.getenv("OPENAI_API_KEY"), env="OPENAI_API_KEY")

    # ─── JWT / Auth ───────────────────────────────────────────────────────────
    JWT_SECRET: str = Field(os.getenv("JWT_SECRET"), env="JWT_SECRET")
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
        
        Returns:
            list[str]: List of CORS origins from the BACKEND_CORS_ORIGINS setting
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

