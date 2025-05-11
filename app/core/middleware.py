from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings


def apply_middlewares(app):
    """
    Apply middleware to the FastAPI application.
    
    Args:
        app: FastAPI application instance
        
    Notes:
        Adds CORS middleware with configuration from settings
        Adds GZip compression for responses over 500 bytes
    """
    # Get origins from settings
    origins = settings.get_cors_origins()
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,  # Required for cookies to work cross-origin
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=500)
