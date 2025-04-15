from datetime import datetime
from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.deps import get_current_active_user
from app.db.database import get_supabase
from app.schemas.users import User, UserUpdate, UserWithStats
from app.schemas.posts import Post
from app.schemas.follows import Follow, FollowCreate

router = APIRouter()


@router.get("/me", response_model=User)
def read_user_me(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user information.
    """
    return current_user


@router.put("/me", response_model=User)
def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Update own user information.
    """
    current_data = current_user.dict()
    update_data = user_update.dict(exclude_unset=True)
    
    if not update_data:
        return current_user
    
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    result = db.table("users").update(update_data).eq("id", str(current_user.id)).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user information",
        )
    
    return User(**result.data[0])


@router.get("/{username}", response_model=UserWithStats)
def get_user_by_username(
    username: str,
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Get user by username.
    """
    user_data = db.table("users").select("*").eq("username", username).execute()
    
    if not user_data.data or len(user_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username {username} not found",
        )
    
    user = user_data.data[0]
    
    # Get posts count
    posts_count = db.table("posts").select("id", count="exact").eq("user_id", user["id"]).execute()
    
    # Get followers count
    followers_count = db.table("follows").select("id", count="exact").eq("followed_id", user["id"]).execute()
    
    # Get following count
    following_count = db.table("follows").select("id", count="exact").eq("follower_id", user["id"]).execute()
    
    user_with_stats = {
        **user,
        "posts_count": posts_count.count if hasattr(posts_count, 'count') else 0,
        "followers_count": followers_count.count if hasattr(followers_count, 'count') else 0,
        "following_count": following_count.count if hasattr(following_count, 'count') else 0,
    }
    
    return UserWithStats(**user_with_stats)


@router.get("/{username}/posts", response_model=List[Post])
def get_user_posts(
    username: str,
    skip: int = 0,
    limit: int = 10,
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Get posts by username.
    """
    user_data = db.table("users").select("*").eq("username", username).execute()
    
    if not user_data.data or len(user_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username {username} not found",
        )
    
    user = user_data.data[0]
    
    posts = db.table("posts") \
        .select("*") \
        .eq("user_id", user["id"]) \
        .order("created_at", desc=True) \
        .range(skip, skip + limit - 1) \
        .execute()
    
    return posts.data


@router.post("/follow", response_model=Follow)
def follow_user(
    follow_data: FollowCreate,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Follow a user.
    """
    # Check if already following
    existing_follow = db.table("follows") \
        .select("*") \
        .eq("follower_id", str(current_user.id)) \
        .eq("followed_id", str(follow_data.followed_id)) \
        .execute()
    
    if existing_follow.data and len(existing_follow.data) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user",
        )
    
    # Check if followed user exists
    followed_user = db.table("users").select("*").eq("id", str(follow_data.followed_id)).execute()
    
    if not followed_user.data or len(followed_user.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User to follow not found",
        )
    
    # Create follow record
    now = datetime.utcnow().isoformat()
    follow_dict = {
        "follower_id": str(current_user.id),
        "followed_id": str(follow_data.followed_id),
        "created_at": now,
    }
    
    result = db.table("follows").insert(follow_dict).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to follow user",
        )
    
    # Create notification
    notification_dict = {
        "user_id": str(follow_data.followed_id),
        "triggered_by_user_id": str(current_user.id),
        "type": "follow",
        "message": f"{current_user.username} started following you",
        "created_at": now,
    }
    
    db.table("notifications").insert(notification_dict).execute()
    
    return Follow(**result.data[0])


@router.delete("/unfollow/{user_id}", response_model=dict)
def unfollow_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Unfollow a user.
    """
    # Check if follow exists
    follow = db.table("follows") \
        .select("*") \
        .eq("follower_id", str(current_user.id)) \
        .eq("followed_id", str(user_id)) \
        .execute()
    
    if not follow.data or len(follow.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not following this user",
        )
    
    # Delete follow
    db.table("follows") \
        .delete() \
        .eq("follower_id", str(current_user.id)) \
        .eq("followed_id", str(user_id)) \
        .execute()
    
    return {"status": "success", "message": "User unfollowed successfully"} 