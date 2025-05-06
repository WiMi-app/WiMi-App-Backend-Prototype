from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.deps import get_current_active_user
from app.core.moderation import moderate_content
from app.schemas.users import User

router = APIRouter()

@router.post("/test", response_model=Dict[str, Any])
async def test_moderation(
    text_content: Optional[str] = Body(None, description="Text content to moderate"),
    image_urls: Optional[List[str]] = Body(None, description="Image URLs to moderate"),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Test the moderation API on provided text and/or images.
    This endpoint is for testing purposes only.
    
    Requires authentication but does not require admin privileges.
    Results will be recorded in moderation statistics.
    """
    if not text_content and not image_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of text_content or image_urls must be provided",
        )
    
    # Call the moderation service
    moderation_result = await moderate_content(
        text_content=text_content,
        image_urls=image_urls
    )
    
    # Return the moderation result with minimal information for security
    return {
        "flagged": moderation_result.flagged,
        "categories": moderation_result.categories,
        "category_scores": moderation_result.category_scores,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/safe-check", response_model=Dict[str, Any])
async def safe_content_check(
    text_content: Optional[str] = Body(None, description="Text content to check"),
    image_urls: Optional[List[str]] = Body(None, description="Image URLs to check"),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Simple boolean check if content is safe or not.
    Returns only a basic result without details for frequent usage.
    
    Requires authentication but does not require admin privileges.
    Results will be recorded in moderation statistics.
    """
    if not text_content and not image_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of text_content or image_urls must be provided",
        )
    
    # Call the moderation service
    moderation_result = await moderate_content(
        text_content=text_content,
        image_urls=image_urls
    )
    
    # Return minimal information
    return {
        "is_safe": not moderation_result.flagged,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/public/test", response_model=Dict[str, Any])
async def public_test_moderation(
    text_content: Optional[str] = Body(None, description="Text content to moderate"),
    image_urls: Optional[List[str]] = Body(None, description="Image URLs to moderate"),
) -> Dict[str, Any]:
    """
    Public endpoint to test the moderation API without authentication.
    This endpoint is for testing and development purposes only.
    
    No authentication required, but has stricter rate limits.
    Results will be recorded in moderation statistics.
    """
    if not text_content and not image_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of text_content or image_urls must be provided",
        )
    
    # Call the moderation service
    moderation_result = await moderate_content(
        text_content=text_content,
        image_urls=image_urls
    )
    
    # Return simplified moderation result for public access
    return {
        "flagged": moderation_result.flagged,
        "categories": moderation_result.categories,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/public/safe-check", response_model=Dict[str, Any])
async def public_safe_content_check(
    text_content: Optional[str] = Body(None, description="Text content to check"),
    image_urls: Optional[List[str]] = Body(None, description="Image URLs to check"),
) -> Dict[str, Any]:
    """
    Public endpoint for a simple boolean check if content is safe or not.
    Returns only a basic result without details.
    
    No authentication required, but has stricter rate limits.
    Results will be recorded in moderation statistics.
    """
    if not text_content and not image_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of text_content or image_urls must be provided",
        )
    
    # Call the moderation service
    moderation_result = await moderate_content(
        text_content=text_content,
        image_urls=image_urls
    )
    
    # Return minimal information for public access
    return {
        "is_safe": not moderation_result.flagged,
        "timestamp": datetime.now().isoformat()
    } 