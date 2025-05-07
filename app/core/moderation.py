import os
import time
from typing import List, Optional, Union, Dict, Any
from openai import OpenAI
from fastapi import HTTPException, status
from pydantic import BaseModel

# Import moderation stats tracker and settings
from app.core.middleware import moderation_stats
from app.core.config import settings

# Initialize the OpenAI client if API key is available
api_key = os.getenv("OPENAI_API_KEY")
client = None

if api_key:
    client = OpenAI(api_key=api_key)
elif settings.ENVIRONMENT == "development":
    # In development, warn but don't fail
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("OPENAI_API_KEY not set, moderation will use mock responses in development mode")
else:
    # In production, warn about missing API key
    import logging
    logger = logging.getLogger(__name__)
    logger.error("OPENAI_API_KEY not set, moderation will fail in production mode")

class ModerationResult(BaseModel):
    flagged: bool
    categories: Dict[str, bool] = {}
    category_scores: Dict[str, float] = {}
    error: Optional[str] = None

async def moderate_content(
    text_content: Optional[str] = None, 
    image_urls: Optional[List[str]] = None
) -> ModerationResult:
    """
    Moderates text and image content using OpenAI's moderation API.
    
    Args:
        text_content: Optional text content to moderate
        image_urls: Optional list of image URLs to moderate
        
    Returns:
        ModerationResult object containing flagged status and details
    """
    start_time = time.time()
    is_flagged = False
    
    # Skip if no content is provided
    if not text_content and not (image_urls and len(image_urls) > 0):
        return ModerationResult(flagged=False)
    
    # In development without API key, provide mock response
    if settings.ENVIRONMENT == "development" and client is None:
        # Check for obvious bad words in development as a simple mock
        bad_words = ["explicit", "violent", "hate", "illegal"]
        
        if text_content and any(word in text_content.lower() for word in bad_words):
            mock_result = ModerationResult(
                flagged=True,
                categories={"harassment": True, "hate": False, "sexual": False, "violence": False},
                category_scores={"harassment": 0.9, "hate": 0.2, "sexual": 0.1, "violence": 0.1}
            )
        else:
            mock_result = ModerationResult(
                flagged=False,
                categories={"harassment": False, "hate": False, "sexual": False, "violence": False},
                category_scores={"harassment": 0.1, "hate": 0.1, "sexual": 0.1, "violence": 0.1}
            )
        
        # Record moderation stats
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        moderation_stats.increment_moderation(was_flagged=mock_result.flagged, processing_time_ms=processing_time)
        
        return mock_result
    
    try:
        # If no OpenAI client is available and we're not in development, fail
        if client is None:
            raise ValueError("OpenAI API key not set")
            
        input_items = []
        
        # Add text content if provided
        if text_content:
            input_items.append({"type": "text", "text": text_content})
        
        # Add image URLs if provided
        if image_urls and len(image_urls) > 0:
            for url in image_urls:
                input_items.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
        
        # Call OpenAI's moderation API
        response = client.moderations.create(
            model="omni-moderation-latest",
            input=input_items
        )
        
        # Process response
        if response.results and len(response.results) > 0:
            # If any content is flagged, the entire submission is flagged
            is_flagged = any(result.flagged for result in response.results)
            
            # Get the most severe categories and scores (using the first flagged result or just the first result)
            flagged_result = next((r for r in response.results if r.flagged), response.results[0])
            
            result = ModerationResult(
                flagged=is_flagged,
                categories=flagged_result.categories.model_dump(),
                category_scores=flagged_result.category_scores.model_dump()
            )
        else:
            result = ModerationResult(flagged=False)
        
    except Exception as e:
        # In development, provide more details about errors
        if settings.ENVIRONMENT == "development":
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Moderation error: {str(e)}")
            
            # In development, don't fail closed for easier testing
            is_flagged = False
            result = ModerationResult(
                flagged=is_flagged,
                error=str(e)
            )
        else:
            # In production, fail closed for safety
            is_flagged = True
            result = ModerationResult(
                flagged=is_flagged,
                error="Moderation service unavailable"
            )
    
    finally:
        # Record moderation stats
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        moderation_stats.increment_moderation(was_flagged=is_flagged, processing_time_ms=processing_time)
        
    return result 