from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from typing import List

from app.schemas.follows import FollowCreate, FollowOut
from app.core.deps import get_current_user, get_supabase

router = APIRouter(prefix="/api/v0/follows", tags=["follows"])

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
    Creates or returns the existing follow for (follower_id, followee_id).
    Uses upsert with on_conflict to ensure idempotency.
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
    rec = supabase.from_("follows").select("follower_id").eq("id", follow_id).single()
    if rec.error or rec.data["follower_id"] != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    res = supabase.from_("follows").delete().eq("id", follow_id)
    if res.error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, res.error.message)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
