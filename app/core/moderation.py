import os
import time
from typing import List, Optional, Union, Dict, Any
from openai import OpenAI
from fastapi import HTTPException, status
from pydantic import BaseModel

# Import moderation stats tracker
from app.core.middleware import moderation_stats

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    
    try:
        # Skip if no content is provided
        if not text_content and not (image_urls and len(image_urls) > 0):
            return ModerationResult(flagged=False)
            
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
        # Log the error in a production system
        is_flagged = True  # Fail closed for safety
        result = ModerationResult(
            flagged=is_flagged,
            error=str(e)
        )
    
    finally:
        # Record moderation stats
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        moderation_stats.increment_moderation(was_flagged=is_flagged, processing_time_ms=processing_time)
        
    return result 