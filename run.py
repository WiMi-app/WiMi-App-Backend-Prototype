import os

import uvicorn
from dotenv import load_dotenv

load_dotenv(".env")

from app.core.config import settings

if __name__ == "__main__":
    """
    Run the application with environment-specific settings.
    """
    # Uvicorn arguments
    uvicorn_kwargs = {
        "app": "app.main:app",  # Use import string instead of imported object
        "port": settings.PORT,
        "log_level": settings.LOG_LEVEL.lower(),
    }

    if settings.ENVIRONMENT == "production":
        # Production: enable real client IPs, forwarded headers, multiple workers
        uvicorn_kwargs.update({
            "host": "0.0.0.0",  # Bind to all interfaces in production
            "workers": int(os.getenv("WORKERS", "4")),
            "proxy_headers": True,
            "forwarded_allow_ips": "*",
        })
    else:
        # Development: auto-reload and single worker
        uvicorn_kwargs.update({
            "host": "127.0.0.1",  # Only bind to localhost in development
            "reload": True,
        })

    uvicorn.run(**uvicorn_kwargs)
