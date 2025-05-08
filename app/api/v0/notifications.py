from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List

from app.schemas.notifications import NotificationOut
from app.core.deps import get_current_user, get_supabase

router = APIRouter(tags=["notifications"])

@router.get(
    "/",
    response_model=List[NotificationOut],
    summary="List your notifications (paginated)",
)
def list_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    start = (page - 1) * per_page
    end = start + per_page - 1
    res = (
        supabase.from_("notifications")
        .select("*")
        .eq("recipient_id", current_user.id)
        .order("created_at", desc=True)
        .range(start, end)
    )
    if res.error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, res.error.message)
    return res.data

@router.post(
    "/read/{notification_id}",
    status_code=status.HTTP_200_OK,
    summary="Mark a single notification as read",
)
def mark_read(
    notification_id: str,
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    rec = supabase.from_("notifications").select("recipient_id").eq("id", notification_id).single()
    if rec.error or rec.data["recipient_id"] != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    upd = (
        supabase.from_("notifications")
        .update({"is_read": True})
        .eq("id", notification_id)
        .single()
    )
    if upd.error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, upd.error.message)
    return {"status": "ok"}

@router.post(
    "/read_all",
    status_code=status.HTTP_200_OK,
    summary="Mark all your notifications as read",
)
def mark_all_read(
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    # Bulk update; returns list of updated IDs
    upd = (
        supabase.from_("notifications")
        .update({"is_read": True})
        .eq("recipient_id", current_user.id)
        .select("id")
    )
    if upd.error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, upd.error.message)
    return {"updated_count": len(upd.data)}
