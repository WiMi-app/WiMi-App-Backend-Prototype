"""
Script to run the WiMi application.
See Dockerfile and docker-compose.yml for production deployment.
"""
import uvicorn
import os
from app.core.config import settings

if __name__ == "__main__":
    """
    Run the application with environment-specific settings.
    """
    if settings.ENVIRONMENT == "production":
        # Production settings
        uvicorn.run(
            "app.main:app", 
            host="0.0.0.0", 
            port=int(os.getenv("PORT", "8000")),
            workers=int(os.getenv("WORKERS", "4")),
            proxy_headers=True
        )
    else:
        # Development settings with auto-reload
        uvicorn.run(
            "app.main:app", 
            port=int(os.getenv("PORT", "8000")), 
            reload=True
        ) 