from pydantic_settings import BaseSettings
from typing import Any, Dict, Optional, List
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check for critical environment variables
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    logger.error("SECRET_KEY environment variable is missing or empty!")
else:
    logger.info("SECRET_KEY loaded successfully")


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Contains all configuration for the application.
    """
    APP_NAME: str = os.getenv("APP_NAME", "WiMi")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # No fallback for production - SECRET_KEY must be set
    SECRET_KEY: str = secret_key or ""
    
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    API_V1_STR: str = "/api/v1"
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "https://wimi-app.vercel.app",
    ]
    
    # Log level configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()

# Verify critical settings
if not settings.SECRET_KEY:
    raise ValueError("Missing SECRET_KEY. This is required for production deployment.")

if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    raise ValueError("Missing Supabase configuration. SUPABASE_URL and SUPABASE_KEY are required.")

# Set log level from environment
logging.getLogger().setLevel(getattr(logging, settings.LOG_LEVEL)) 