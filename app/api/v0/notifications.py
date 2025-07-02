from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_current_user, get_supabase
from app.schemas.notifications import NotificationOut, NotificationStatus

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
    """
    List notifications for the current user with pagination.
    
    Args:
        page (int): Page number (starting from 1)
        per_page (int): Items per page (max 100)
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        
    Returns:
        List[NotificationOut]: Paginated list of notifications
        
    Raises:
        HTTPException: 400 if database operation fails
    """
    try:
        start = (page - 1) * per_page
        end = start + per_page - 1
        
        resp = supabase.table("notifications")\
            .select("*") \
            .eq("user_id", current_user.id) \
            .order("created_at", desc=True) \
            .range(start, end) \
            .execute()
            
        # Transform the data to match the expected schema
        transformed_data = []
        for notification in resp.data:
            # Map the triggered_by_user_id to triggered_by_id for schema compatibility
            if "triggered_by_user_id" in notification:
                notification["triggered_by_id"] = notification.pop("triggered_by_user_id")
            
            # Ensure comment_id is a string or None
            if notification.get("comment_id") is None:
                notification["comment_id"] = None
                
            transformed_data.append(notification)
        
        return transformed_data
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error fetching notifications: {str(e)}")

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
    """
    Mark a specific notification as read.
    
    Args:
        notification_id (str): UUID of the notification to mark as read
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        
    Returns:
        dict: Success status
        
    Raises:
        HTTPException: 403 if user is not authorized to modify the notification
        HTTPException: 400 if database operation fails
    """
    try:
        # Check if notification exists and belongs to user
        rec = supabase.table("notifications")\
            .select("user_id")\
            .eq("id", notification_id)\
            .execute()
            
        if not rec.data or len(rec.data) == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
            
        if rec.data[0]["user_id"] != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to mark this notification as read")
            
        # Update notification
        supabase.table("notifications")\
            .update({"is_read": True})\
            .eq("id", notification_id)\
            .execute()
            
        return {"status": "ok"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error marking notification as read: {str(e)}")

@router.post(
    "/read_all",
    status_code=status.HTTP_200_OK,
    summary="Mark all your notifications as read",
)
def mark_all_read(
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """
    Mark all notifications for the current user as read.
    
    Args:
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        
    Returns:
        dict: Count of updated notifications
        
    Raises:
        HTTPException: 400 if database operation fails
    """
    try:
        # Get the count of unread notifications
        unread_count = supabase.table("notifications")\
            .select("id")\
            .eq("user_id", current_user.id)\
            .eq("is_read", False)\
            .execute()
            
        # Update all notifications to read
        supabase.table("notifications")\
            .update({"is_read": True})\
            .eq("user_id", current_user.id)\
            .eq("is_read", False)\
            .execute()
            
        return {"updated_count": len(unread_count.data) if unread_count.data else 0}
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error marking all notifications as read: {str(e)}")

# Additional endpoint for creating scheduled notifications if needed
@router.post(
    "/schedule",
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a notification to be sent later",
)
def schedule_notification(
    type: str,
    user_id: str,
    triggered_by_id: str,
    post_id: str = "",
    comment_id: str = "",
    message: str = "",
    send_at: datetime = datetime(2000, 1, 1, 0, 0, 0, 0),
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """
    Schedule a notification to be sent at a specified time.
    This requires a cron job to actually deliver the notifications.
    
    Args:
        type (str): Type of notification
        user_id (str): User ID to receive the notification
        triggered_by_id (str): User ID who triggered this notification
        post_id (str, optional): ID of the related post
        comment_id (str, optional): ID of the related comment
        message (str, optional): Notification message
        send_at (datetime, optional): When to send the notification
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        
    Returns:
        dict: Details of scheduled notification
        
    Raises:
        HTTPException: 400 if database operation fails
    """
    try:
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        send_time = send_at.strftime("%Y-%m-%dT%H:%M:%S.%f") if send_at else now
        
        notification_data = {
            "type": type,
            "user_id": user_id,
            "triggered_by_user_id": triggered_by_id,  # Map to database column name
            "post_id": post_id,
            "comment_id": comment_id if comment_id else None,
            "message": message,
            "is_read": False,
            "created_at": now,
            "status": NotificationStatus.PENDING
        }
        
        resp = supabase.table("notifications").insert(notification_data).execute()
        
        if not resp.data:
            raise HTTPException(status_code=400, detail="Failed to schedule notification")
        
        # Transform response to match schema before returning
        result = resp.data[0]
        if "triggered_by_user_id" in result:
            result["triggered_by_id"] = result.pop("triggered_by_user_id")
            
        return result
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error scheduling notification: {str(e)}")
