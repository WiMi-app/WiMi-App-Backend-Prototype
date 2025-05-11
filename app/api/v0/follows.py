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
        payload (FollowCreate): Contains followee_id of the user to follow
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        idempotency_key: Optional key for idempotent requests
        
    Returns:
        FollowOut: The created follow relationship
        
    Raises:
        HTTPException: 400 if user tries to follow themselves
        HTTPException: 400 if database operation fails
    """
    if payload.followee_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot follow yourself")

    data = {"follower_id": current_user.id, "followee_id": payload.followee_id}
    res = (
        supabase.from_("follows")
        .upsert(data, on_conflict=["follower_id", "followee_id"])
        .single()
    )
    if res.error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, res.error.message)
    return res.data

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
    rec = supabase.from_("follows").select("follower_id").eq("id", follow_id).single()
    if rec.error or rec.data["follower_id"] != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    res = supabase.from_("follows").delete().eq("id", follow_id)
    if res.error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, res.error.message)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
