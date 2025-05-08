from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from supabase import create_client, Client

class Settings(BaseSettings):
    # ─── App Metadata ────────────────────────────────────────────────────────
    APP_NAME: str = Field("WiMi", env="APP_NAME")
    APP_VERSION: str = Field("0.1.0", env="APP_VERSION")
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    PORT: int = Field(8000, env="PORT")
    API_V1_STR: str = Field("/api/v0", env="API_V1_STR")

    # ─── Supabase ─────────────────────────────────────────────────────────────
    SUPABASE_URL: str = Field("", env="SUPABASE_URL")
    SUPABASE_KEY: str         = Field("", env="SUPABASE_KEY")

    # ─── OpenAI ─────────────────────────────────────────────────────────────
    OPENAI_KEY: str = Field("", env="OPENAI_API_KEY")

    # ─── JWT / Auth ───────────────────────────────────────────────────────────
    JWT_SECRET: str = Field("", env="SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        60, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # ─── CORS ─────────────────────────────────────────────────────────────────
    # Plain string here; you'll split it in your code or middleware if needed.
    BACKEND_CORS_ORIGINS: str = Field("", env="BACKEND_CORS_ORIGINS")

    # ─── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")

    # ─── Pydantic-Settings Config ─────────────────────────────────────────────
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",         # drop any unknown env vars (OPENAI_API_KEY, etc.)
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
