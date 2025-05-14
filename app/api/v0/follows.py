from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.core.deps import get_current_user, get_supabase
from app.schemas.follows import FollowCreate, FollowOut

router = APIRouter(tags=["follows"])

@router.post(
    "/",
    response_model=FollowOut,
    status_code=status.HTTP_201_CREATED,
    summary="Follow a user (idempotent)",
)
def follow_user(
    payload: FollowCreate,
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """
    Create a follow relationship between the current user and another user.
    
    Args:
        payload (FollowCreate): Contains followed_id (or followee_id) of the user to follow
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        idempotency_key: Optional key for idempotent requests
        
    Returns:
        FollowOut: The created follow relationship
        
    Raises:
        HTTPException: 400 if user tries to follow themselves
        HTTPException: 400 if database operation fails
    """
    # The followed_id is guaranteed to be set by the model_validator in FollowCreate
    if payload.followed_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot follow yourself")

    try:
        # First check if the follow relationship already exists
        existing = supabase.table("follows").select("*") \
            .eq("follower_id", current_user.id) \
            .eq("followed_id", payload.followed_id) \
            .execute()
            
        # If relationship exists, return it
        if existing.data and len(existing.data) > 0:
            return existing.data[0]
            
        # Otherwise create new follow relationship
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")
        data = {
            "follower_id": current_user.id, 
            "followed_id": payload.followed_id,
            "created_at": now
        }
        
        res = supabase.table("follows").insert(data).execute()
        
        if not res.data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to create follow relationship")
            
        return res.data[0]
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error creating follow relationship: {str(e)}")

@router.delete(
    "/{follow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unfollow a user",
)
def unfollow_user(
    follow_id: str,
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """
    Remove a follow relationship by its ID.
    
    Args:
        follow_id (str): UUID of the follow relationship to delete
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        
    Returns:
        Response: 204 No Content on success
        
    Raises:
        HTTPException: 403 if user is not authorized to delete the follow
        HTTPException: 400 if database operation fails
    """
    try:
        # Check if follow relationship exists and belongs to current user
        rec = supabase.table("follows").select("follower_id").eq("id", follow_id).execute()
        
        if not rec.data or len(rec.data) == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Follow relationship not found")
            
        if rec.data[0]["follower_id"] != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to delete this follow relationship")
            
        # Delete the follow relationship
        supabase.table("follows").delete().eq("id", follow_id).execute()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error deleting follow relationship: {str(e)}")
