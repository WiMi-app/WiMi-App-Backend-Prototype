from supabase import create_client, Client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

try:
    supabase: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    raise

def get_supabase() -> Client:
    """
    Returns Supabase client instance.
    Used as a dependency in FastAPI routes to access the database.
    
    Returns:
        Client: Initialized Supabase client
    """
    return supabase 