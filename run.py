import os
from dotenv import load_dotenv
import uvicorn

load_dotenv(".env")

from app.main import app
from app.core.config import settings

if __name__ == "__main__":
    """
    Run the application with environment-specific settings.
    """
    # Uvicorn arguments
    uvicorn_kwargs = {
        "app": app,                
        "host": "0.0.0.0",
        "port": settings.PORT,
        "log_level": settings.LOG_LEVEL.lower(),
    }

    if settings.ENVIRONMENT == "production":
        # Production: enable real client IPs, forwarded headers, multiple workers
        uvicorn_kwargs.update({
            "workers": int(os.getenv("WORKERS", "4")),
            "proxy_headers": True,
            "forwarded_allow_ips": "*",
        })
    else:
        # Development: auto-reload and single worker
        uvicorn_kwargs["reload"] = True

    uvicorn.run(app)
