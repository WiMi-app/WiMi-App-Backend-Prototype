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
    res = (
        supabase.from_("likes")
        .upsert(data, on_conflict=["user_id", "post_id"])
        .single()
    )
    if res.error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, res.error.message)
    return res.data

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
    rec = supabase.from_("likes").select("user_id").eq("id", like_id).single()
    if rec.error or rec.data["user_id"] != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    res = supabase.from_("likes").delete().eq("id", like_id)
    if res.error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, res.error.message)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
