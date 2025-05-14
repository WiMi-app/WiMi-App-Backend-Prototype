from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.core.deps import get_current_user, get_supabase
from app.schemas.likes import LikeCreate, LikeOut

router = APIRouter(tags=["likes"])

@router.post(
    "/",
    response_model=LikeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Like a post (idempotent)",
)
def like_post(
    payload: LikeCreate,
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """
    Create a like for a post by the current user.
    
    Args:
        payload (LikeCreate): Contains post_id to like
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        idempotency_key: Optional key for idempotent requests
        
    Returns:
        LikeOut: The created like record
        
    Raises:
        HTTPException: 400 if database operation fails
    """
    data = {"user_id": current_user.id, "post_id": payload.post_id}
    try:
        # First check if like already exists
        existing = supabase.table("likes").select("*") \
            .eq("user_id", current_user.id) \
            .eq("post_id", payload.post_id) \
            .execute()
            
        # If like exists, return it
        if existing.data and len(existing.data) > 0:
            return existing.data[0]
            
        # Otherwise create new like
        res = supabase.table("likes").insert(data).execute()
        if not res.data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to create like")
        return res.data[0]
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error: {str(e)}")

@router.delete(
    "/{like_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a like",
)
def unlike_post(
    like_id: str,
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """
    Remove a like by its ID.
    
    Args:
        like_id (str): UUID of the like to remove
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        
    Returns:
        Response: 204 No Content on success
        
    Raises:
        HTTPException: 403 if user is not authorized to remove the like
        HTTPException: 400 if database operation fails
    """
    try:
        # Check if like exists and belongs to current user
        rec = supabase.table("likes").select("user_id").eq("id", like_id).execute()
        
        if not rec.data or len(rec.data) == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Like not found")
            
        if rec.data[0]["user_id"] != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
            
        # Delete the like
        supabase.table("likes").delete().eq("id", like_id).execute()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error: {str(e)}")
