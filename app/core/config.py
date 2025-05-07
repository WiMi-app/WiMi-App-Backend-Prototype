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
    logger.warning("SECRET_KEY environment variable is missing or empty! Using development fallback key.")
    secret_key = "development_secret_key_not_for_production"
else:
    logger.info("SECRET_KEY loaded successfully")


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Contains all configuration for the application.
    """
    APP_NAME: str = os.getenv("APP_NAME", "WiMi")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Secret key with fallback for development
    SECRET_KEY: str = secret_key
    
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "14400"))  # 10 days
    
    API_V1_STR: str = "/api/v1"
    
    # CORS Configuration - broader for development
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",  # Vite default
        "*"  # Allow all origins in development
    ]
    
    # Log level configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG" if ENVIRONMENT == "development" else "INFO")
    
    # Development-only settings
    MOCK_AUTH: bool = os.getenv("MOCK_AUTH", "False").lower() == "true"
    DISABLE_RATE_LIMITS: bool = os.getenv("DISABLE_RATE_LIMITS", "True" if ENVIRONMENT == "development" else "False").lower() == "true"
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()

# Verify critical settings with development fallbacks
if not settings.SECRET_KEY:
    logger.warning("Using insecure default SECRET_KEY. This is only acceptable for development.")
    settings.SECRET_KEY = "insecure_development_key_please_change_in_production"

if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    if settings.ENVIRONMENT == "development":
        logger.warning("Missing Supabase configuration. Using mock database in development mode.")
    else:
        raise ValueError("Missing Supabase configuration. SUPABASE_URL and SUPABASE_KEY are required for production.")

# Set log level from environment
logging.getLogger().setLevel(getattr(logging, settings.LOG_LEVEL)) 