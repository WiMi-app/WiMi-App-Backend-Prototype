from datetime import datetime
from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.deps import get_current_active_user
from app.db.database import get_supabase
from app.schemas.likes import Like, LikeCreate
from app.schemas.users import User

router = APIRouter()


@router.post("/", response_model=Like)
def create_like(
    like_data: LikeCreate,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Like a post or comment.
    """
    # Check if already liked
    query = db.table("likes").select("*").eq("user_id", str(current_user.id))
    
    if like_data.post_id:
        query = query.eq("post_id", str(like_data.post_id))
        
        # Check if post exists
        post = db.table("posts").select("*").eq("id", str(like_data.post_id)).execute()
        
        if not post.data or len(post.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with ID {like_data.post_id} not found",
            )
    
    if like_data.comment_id:
        query = query.eq("comment_id", str(like_data.comment_id))
        
        # Check if comment exists
        comment = db.table("comments").select("*").eq("id", str(like_data.comment_id)).execute()
        
        if not comment.data or len(comment.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment with ID {like_data.comment_id} not found",
            )
    
    existing_like = query.execute()
    
    if existing_like.data and len(existing_like.data) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already liked this content",
        )
    
    # Create like
    now = datetime.utcnow().isoformat()
    like_dict = {
        "user_id": str(current_user.id),
        "created_at": now,
    }
    
    if like_data.post_id:
        like_dict["post_id"] = str(like_data.post_id)
    
    if like_data.comment_id:
        like_dict["comment_id"] = str(like_data.comment_id)
    
    result = db.table("likes").insert(like_dict).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create like",
        )
    
    # Create notification
    if like_data.post_id:
        post_data = post.data[0]
        user_id = post_data["user_id"]
        
        if user_id != str(current_user.id):
            notification_dict = {
                "user_id": user_id,
                "triggered_by_user_id": str(current_user.id),
                "post_id": str(like_data.post_id),
                "type": "like_post",
                "message": f"{current_user.username} liked your post",
                "created_at": now,
            }
            
            db.table("notifications").insert(notification_dict).execute()
    
    if like_data.comment_id:
        comment_data = comment.data[0]
        user_id = comment_data["user_id"]
        
        if user_id != str(current_user.id):
            notification_dict = {
                "user_id": user_id,
                "triggered_by_user_id": str(current_user.id),
                "comment_id": str(like_data.comment_id),
                "type": "like_comment",
                "message": f"{current_user.username} liked your comment",
                "created_at": now,
            }
            
            db.table("notifications").insert(notification_dict).execute()
    
    return Like(**result.data[0])


@router.delete("/post/{post_id}", response_model=dict)
def delete_post_like(
    post_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Unlike a post.
    """
    like = db.table("likes") \
        .select("*") \
        .eq("user_id", str(current_user.id)) \
        .eq("post_id", str(post_id)) \
        .execute()
    
    if not like.data or len(like.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found",
        )
    
    db.table("likes") \
        .delete() \
        .eq("user_id", str(current_user.id)) \
        .eq("post_id", str(post_id)) \
        .execute()
    
    return {"status": "success", "message": "Post unliked successfully"}


@router.delete("/comment/{comment_id}", response_model=dict)
def delete_comment_like(
    comment_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Unlike a comment.
    """
    like = db.table("likes") \
        .select("*") \
        .eq("user_id", str(current_user.id)) \
        .eq("comment_id", str(comment_id)) \
        .execute()
    
    if not like.data or len(like.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found",
        )
    
    db.table("likes") \
        .delete() \
        .eq("user_id", str(current_user.id)) \
        .eq("comment_id", str(comment_id)) \
        .execute()
    
    return {"status": "success", "message": "Comment unliked successfully"} 