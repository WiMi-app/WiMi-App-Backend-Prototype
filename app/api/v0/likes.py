from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from typing import List

from app.schemas.likes import LikeCreate, LikeOut
from app.core.deps import get_current_user, get_supabase

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
    Creates or returns the existing like for (user_id, post_id).
    Uses upsert with on_conflict to ensure idempotency.
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
    rec = supabase.from_("likes").select("user_id").eq("id", like_id).single()
    if rec.error or rec.data["user_id"] != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    res = supabase.from_("likes").delete().eq("id", like_id)
    if res.error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, res.error.message)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
