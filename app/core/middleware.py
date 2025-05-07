"""
Middleware implementations for the application.
Includes API usage tracking and other request processing middleware.
"""
from datetime import datetime, timedelta
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from uuid import uuid4
import json
from typing import Dict, Callable, Any
import os

from app.core.config import settings

logger = logging.getLogger(__name__)

# Simple in-memory storage for tracking API usage statistics
# In a production app, you would use Redis or a database for this
class ModerationStats:
    def __init__(self):
        self.reset()
        self.enabled = not (settings.ENVIRONMENT == "development" and 
                         os.getenv("DISABLE_MODERATION_STATS", "False").lower() == "true")
    
    def reset(self):
        self.total_moderations = 0
        self.flagged_content = 0
        self.moderation_time_ms = 0
        self.last_reset = datetime.now()
        self.hourly_counts: Dict[str, int] = {}
    
    def increment_moderation(self, was_flagged: bool, processing_time_ms: float):
        if not self.enabled:
            # Skip stats tracking if disabled in development
            return
            
        self.total_moderations += 1
        
        if was_flagged:
            self.flagged_content += 1
            
        self.moderation_time_ms += processing_time_ms
        
        # Track hourly stats
        hour_key = datetime.now().strftime('%Y-%m-%d %H:00')
        self.hourly_counts[hour_key] = self.hourly_counts.get(hour_key, 0) + 1
        
        # Auto-reset stats after 24 hours to prevent memory growth
        if datetime.now() - self.last_reset > timedelta(hours=24):
            old_total = self.total_moderations
            old_flagged = self.flagged_content
            self.reset()
            # Carry over today's stats
            self.total_moderations = self.hourly_counts.get(hour_key, 0)
            self.flagged_content = old_flagged if old_total == 0 else int(old_flagged * (self.total_moderations / old_total))
    
    def get_stats(self):
        if not self.enabled:
            return {
                "status": "disabled",
                "environment": settings.ENVIRONMENT
            }
            
        avg_time = 0 if self.total_moderations == 0 else self.moderation_time_ms / self.total_moderations
        
        return {
            "total_moderations": self.total_moderations,
            "flagged_content_count": self.flagged_content,
            "flagged_percentage": 0 if self.total_moderations == 0 else (self.flagged_content / self.total_moderations) * 100,
            "avg_processing_time_ms": avg_time,
            "hourly_counts": dict(sorted(self.hourly_counts.items())),
            "stats_since": self.last_reset.isoformat()
        }


# Create a global instance
moderation_stats = ModerationStats()


class APIUsageMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API usage and apply rate limiting if needed.
    
    Logs request data including path, method, processing time,
    client IP, and assigns a unique request ID.
    """
    
    def __init__(self, app):
        super().__init__(app)
        # Skip detailed logging in development if configured
        self.skip_logging = (
            settings.ENVIRONMENT == "development" and
            os.getenv("DISABLE_API_LOGGING", "False").lower() == "true"
        )
        
        if self.skip_logging:
            logger.info("API Usage logging is disabled in development mode")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request, track API usage, and handle errors.
        
        Args:
            request: The incoming request
            call_next: The next middleware in the chain
            
        Returns:
            Response: The response after processing
        """
        start_time = time.time()
        request_id = str(uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Get client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        client_ip = forwarded_for.split(",")[0] if forwarded_for else request.client.host
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add custom headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            # Skip detailed logging in development if configured
            if not self.skip_logging:
                # Log API usage
                self._log_api_call(
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    client_ip=client_ip,
                    status_code=response.status_code,
                    process_time=process_time,
                )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # Always log errors, even in development
            log_level = logging.ERROR
            log_msg = (
                f"Request failed: {str(e)}, "
                f"path={request.url.path}, "
                f"method={request.method}, "
                f"request_id={request_id}, "
                f"time={process_time:.4f}s"
            )
            
            # In development, show error details
            if settings.ENVIRONMENT == "development":
                import traceback
                logger.error(f"{log_msg}\n{traceback.format_exc()}")
            else:
                logger.error(log_msg)
                
            raise
    
    def _log_api_call(
        self, 
        request_id: str,
        method: str,
        path: str,
        client_ip: str,
        status_code: int,
        process_time: float
    ) -> None:
        """
        Log API call details for monitoring and analytics.
        
        Args:
            request_id: Unique identifier for the request
            method: HTTP method used
            path: Request path
            client_ip: Client IP address
            status_code: HTTP status code of the response
            process_time: Time taken to process the request
        """
        # Skip static paths and health check in logs to reduce noise
        if "/static/" in path or path == "/health" or path == "/api/health":
            return
            
        log_data = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "client_ip": client_ip,
            "status_code": status_code,
            "process_time": f"{process_time:.4f}s",
            "environment": settings.ENVIRONMENT
        }
        
        # Log in structured format
        log_level = logging.INFO
        if 400 <= status_code < 500:
            log_level = logging.WARNING
        elif status_code >= 500:
            log_level = logging.ERROR
            
        logger.log(log_level, f"API Call: {json.dumps(log_data)}") 