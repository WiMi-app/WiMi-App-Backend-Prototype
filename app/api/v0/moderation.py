from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.core.moderation import moderate_content
from app.schemas.users import UserOut

router = APIRouter(tags=["moderation"])

@router.post("/test")
async def test_moderation(
    text: str,
    content_type: str = "post",
    user=Depends(get_current_user)
):
    """
    Test the moderation system with provided text.
    
    This endpoint allows testing OpenAI's moderation API with arbitrary text
    to see if it would be flagged. This is useful for testing and debugging
    the moderation system.
    
    Note: This endpoint does not store any data and is intended for testing only.
    
    Args:
        text: The text to check with the moderation system
        content_type: The type of content (post or challenge)
        user: Current authenticated user (only users can access this endpoint)
        
    Returns:
        dict: Moderation results including whether the content was flagged and why
        
    Raises:
        HTTPException: 400 if the test fails
    """
    try:
        # Test the content without raising an exception
        is_safe, results = await moderate_content(text, raise_exception=False, content_type=content_type)
        
        return {
            "text": text,
            "is_safe": is_safe,
            "content_type": content_type,
            "results": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error testing moderation: {str(e)}"
        )

@router.post("/check-text")
async def check_text_moderation(
    text: str,
    content_type: str = "post",
):
    """
    Public endpoint to check if text would pass moderation.
    
    This endpoint allows checking text against the moderation system
    without requiring authentication. This is useful for client applications
    to pre-check content before submission.
    
    Note: This endpoint does not store any data and only returns whether 
    the content would be flagged, not the detailed results.
    
    Args:
        text: The text to check with the moderation system
        content_type: The type of content (post or challenge)
        
    Returns:
        dict: Simple result indicating if the content would pass moderation
    """
    try:
        # Check the content without raising an exception
        is_safe, results = await moderate_content(text, raise_exception=False, content_type=content_type)
        
        response_data = {
            "would_pass": is_safe,
            "content_type": content_type,
        }
        # Add error details if present (e.g., if the moderation API call failed)
        if "error" in results:
            response_data["error"] = results["error"]
        if not is_safe:
             response_data["details"] = results # include full details if flagged or error

        return response_data
    except Exception as e: # Should ideally not be hit if moderate_content handles its errors properly
        # Return an error but still with 200 status code for this public check
        return {
            "would_pass": False,
            "content_type": content_type,
            "error": f"Unexpected error during moderation check: {str(e)}"
        } 