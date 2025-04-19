from pydantic_settings import BaseSettings
from typing import Any, Dict, Optional, List
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check for critical environment variables
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    logger.error("SECRET_KEY environment variable is missing or empty!")
else:
    logger.info(f"SECRET_KEY loaded successfully (length: {len(secret_key)})")

class Settings(BaseSettings):
    APP_NAME: str = os.getenv("APP_NAME", "WiMi")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    SECRET_KEY: str = secret_key or ""
    if not SECRET_KEY:
        # Fallback for development only (do not use in production)
        SECRET_KEY = "insecure_fallback_key_for_development_only"
        logger.warning("Using insecure fallback SECRET_KEY - DO NOT USE IN PRODUCTION")
    
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    API_V1_STR: str = "/api/v1"
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        # "https://wimi-app.vercel.app",
    ]
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()

# Final verification
if settings.SECRET_KEY == "insecure_fallback_key_for_development_only":
    logger.error("WARNING: Using fallback SECRET_KEY. Set proper SECRET_KEY in .env file!") 