from fastapi import APIRouter, Depends, HTTPException, status, Body
from app.core.deps import get_current_active_user, check_if_admin
from app.schemas.users import User
from app.core.middleware import moderation_stats
from app.core.moderation import moderate_content
from datetime import datetime
from typing import Dict, Any, List, Optional

router = APIRouter()

@router.get("/moderation/stats", response_model=Dict[str, Any])
async def get_moderation_stats(
    current_user: User = Depends(get_current_active_user),
    is_admin: bool = Depends(check_if_admin)
) -> Dict[str, Any]:
    """
    Get moderation statistics.
    Requires admin privileges.
    """
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access admin endpoints",
        )
    
    stats = moderation_stats.get_stats()
    
    # Add server time for reference
    stats["server_time"] = datetime.now().isoformat()
    
    return stats


@router.post("/moderation/reset-stats", response_model=Dict[str, str])
async def reset_moderation_stats(
    current_user: User = Depends(get_current_active_user),
    is_admin: bool = Depends(check_if_admin)
) -> Dict[str, str]:
    """
    Reset moderation statistics.
    Requires admin privileges.
    """
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access admin endpoints",
        )
    
    moderation_stats.reset()
    
    return {
        "status": "success",
        "message": "Moderation statistics have been reset",
        "reset_time": datetime.now().isoformat()
    }


@router.post("/moderation/test", response_model=Dict[str, Any])
async def test_moderation(
    text_content: Optional[str] = Body(None, description="Text content to moderate"),
    image_urls: Optional[List[str]] = Body(None, description="Image URLs to moderate"),
    current_user: User = Depends(get_current_active_user),
    is_admin: bool = Depends(check_if_admin)
) -> Dict[str, Any]:
    """
    Test moderation API on provided text and/or images.
    This endpoint is for testing purposes only.
    Requires admin privileges.
    """
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access admin endpoints",
        )
    
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
    
    # Return the moderation result along with the input for reference
    return {
        "input": {
            "text_content": text_content,
            "image_urls": image_urls
        },
        "moderation_result": moderation_result.model_dump(),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/moderation/test-bulk", response_model=List[Dict[str, Any]])
async def test_bulk_moderation(
    content_items: List[Dict[str, Any]] = Body(..., description="List of content items to moderate. Each item should have text_content and/or image_urls"),
    current_user: User = Depends(get_current_active_user),
    is_admin: bool = Depends(check_if_admin)
) -> List[Dict[str, Any]]:
    """
    Test moderation API on multiple content items at once.
    This endpoint is for testing purposes only.
    Requires admin privileges.
    
    Each item in the content_items list should be in the format:
    {
        "text_content": "optional text to moderate",
        "image_urls": ["optional_image_url1", "optional_image_url2"]
    }
    """
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access admin endpoints",
        )
    
    if not content_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The content_items list cannot be empty",
        )
    
    results = []
    
    for item in content_items:
        text_content = item.get("text_content")
        image_urls = item.get("image_urls")
        
        if not text_content and not image_urls:
            # Skip empty items
            continue
        
        # Call the moderation service
        moderation_result = await moderate_content(
            text_content=text_content,
            image_urls=image_urls
        )
        
        # Add result
        results.append({
            "input": {
                "text_content": text_content,
                "image_urls": image_urls
            },
            "moderation_result": moderation_result.model_dump(),
            "timestamp": datetime.now().isoformat()
        })
    
    return results 