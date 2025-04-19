from datetime import datetime, timedelta
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Dict, Callable

# Simple in-memory storage for tracking API usage statistics
# In a production app, you would use Redis or a database for this
class ModerationStats:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.total_moderations = 0
        self.flagged_content = 0
        self.moderation_time_ms = 0
        self.last_reset = datetime.now()
        self.hourly_counts: Dict[str, int] = {}
    
    def increment_moderation(self, was_flagged: bool, processing_time_ms: float):
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
    """Middleware to track API usage and performance."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Record start time
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Add the processing time header to all responses
        response.headers["X-Process-Time-Ms"] = str(int(process_time))
        
        return response 