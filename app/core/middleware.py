from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class MaxUploadSizeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit the size of uploaded files.
    
    Attributes:
        max_size: Maximum upload size in bytes
    """
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10 MB default
        super().__init__(app)
        self.max_size = max_size
        
    async def dispatch(self, request, call_next):
        if request.method == "POST" and request.headers.get("content-type", "").startswith("multipart/form-data"):
            content_length = request.headers.get("content-length")
            if content_length:
                if int(content_length) > self.max_size:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"Upload size exceeds maximum allowed ({self.max_size // (1024 * 1024)} MB)"}
                    )
        return await call_next(request)


def apply_middlewares(app: FastAPI):
    """
    Apply middleware to the FastAPI application.
    
    Args:
        app: FastAPI application instance
        
    Notes:
        - Adds CORS middleware with configuration from settings
        - Adds GZip compression for responses over 500 bytes
        - Adds max upload size middleware (20MB limit)
    """
    # Get origins from settings
    origins = settings.get_cors_origins()
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,  # Required for cookies to work cross-origin
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],  # Needed for file downloads
    )
    
    # Add GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=500)
    
    # Add max upload size middleware - 20MB limit for images
    app.add_middleware(MaxUploadSizeMiddleware, max_size=20 * 1024 * 1024)  # 20 MB
