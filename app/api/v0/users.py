from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.deps import get_current_active_user
from app.db.database import get_supabase
from app.schemas.users import User, UserUpdate, UserWithStats
from app.schemas.posts import Post
from app.schemas.follows import Follow, FollowCreate
from app.core.security import get_password_hash

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
    current_data = current_user.model_dump()
    update_data = user_update.model_dump_json_safe()
    
    if not update_data:
        return current_user
    
    # Handle password update separately
    if "password" in update_data and update_data["password"]:
        # Hash the new password
        password_hash = get_password_hash(update_data["password"])
        # Replace password with password_hash in the update data
        update_data["password_hash"] = password_hash
        # Remove the plain password from update data
        del update_data["password"]
    
    update_data["updated_at"] = datetime.now().isoformat()
    
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
    
    # Get created challenges count
    created_challenges_count = db.table("challenges").select("id", count="exact").eq("creator_id", user["id"]).execute()
    
    # Get joined challenges count
    joined_challenges_count = db.table("challenge_participants").select("challenge_id", count="exact").eq("user_id", user["id"]).execute()
    
    # Get achievements count
    achievements_count = db.table("challenge_achievements").select("id", count="exact").eq("user_id", user["id"]).execute()
    
    user_with_stats = {
        **user,
        "posts_count": posts_count.count if hasattr(posts_count, 'count') else 0,
        "followers_count": followers_count.count if hasattr(followers_count, 'count') else 0,
        "following_count": following_count.count if hasattr(following_count, 'count') else 0,
        "created_challenges_count": created_challenges_count.count if hasattr(created_challenges_count, 'count') else 0,
        "joined_challenges_count": joined_challenges_count.count if hasattr(joined_challenges_count, 'count') else 0,
        "achievements_count": achievements_count.count if hasattr(achievements_count, 'count') else 0,
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
    now = datetime.now().isoformat()
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
            detail="You are not following this user",
        )
    
    # Delete follow record
    db.table("follows") \
        .delete() \
        .eq("follower_id", str(current_user.id)) \
        .eq("followed_id", str(user_id)) \
        .execute()
    
    return {"message": "Successfully unfollowed user", "status": "success"}


@router.get("/{username}/created-challenges", response_model=List[dict])
def get_user_created_challenges(
    username: str,
    skip: int = 0,
    limit: int = 10,
    db: Client = Depends(get_supabase),
    current_user: Optional[User] = Depends(get_current_active_user),
) -> Any:
    """
    Get challenges created by a specific user.
    """
    user_data = db.table("users").select("*").eq("username", username).execute()
    
    if not user_data.data or len(user_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username {username} not found",
        )
    
    user = user_data.data[0]
    
    # Get challenges created by the user
    challenges = db.table("challenges") \
        .select("*") \
        .eq("creator_id", user["id"]) \
        .order("created_at", desc=True) \
        .range(skip, skip + limit - 1) \
        .execute()
    
    if not challenges.data:
        return []
    
    result = []
    
    for challenge in challenges.data:
        # Skip private challenges if current user is not the creator
        if challenge["is_private"] and (not current_user or str(current_user.id) != challenge["creator_id"]):
            # Unless they're a participant
            if current_user:
                participant = db.table("challenge_participants") \
                    .select("*") \
                    .eq("challenge_id", challenge["id"]) \
                    .eq("user_id", str(current_user.id)) \
                    .execute()
                
                if not participant.data or len(participant.data) == 0:
                    continue
            else:
                continue
        
        # Get participants count
        participants_count = db.table("challenge_participants") \
            .select("user_id", count="exact") \
            .eq("challenge_id", challenge["id"]) \
            .execute()
        
        # Get posts count
        posts_count = db.table("challenge_posts") \
            .select("post_id", count="exact") \
            .eq("challenge_id", challenge["id"]) \
            .execute()
        
        # Check if current user is joined
        is_joined = False
        if current_user:
            joined = db.table("challenge_participants") \
                .select("*") \
                .eq("challenge_id", challenge["id"]) \
                .eq("user_id", str(current_user.id)) \
                .execute()
            
            is_joined = joined.data and len(joined.data) > 0
        
        challenge_with_details = {
            **challenge,
            "creator": user,
            "participant_count": participants_count.count if hasattr(participants_count, 'count') else 0,
            "posts_count": posts_count.count if hasattr(posts_count, 'count') else 0,
            "is_joined": is_joined,
        }
        
        result.append(challenge_with_details)
    
    return result


@router.get("/{username}/joined-challenges", response_model=List[dict])
def get_user_joined_challenges(
    username: str,
    skip: int = 0,
    limit: int = 10,
    db: Client = Depends(get_supabase),
    current_user: Optional[User] = Depends(get_current_active_user),
) -> Any:
    """
    Get challenges joined by a specific user.
    """
    user_data = db.table("users").select("*").eq("username", username).execute()
    
    if not user_data.data or len(user_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username {username} not found",
        )
    
    user = user_data.data[0]
    
    # Get challenge participations for the user
    participations = db.table("challenge_participants") \
        .select("*") \
        .eq("user_id", user["id"]) \
        .order("joined_at", desc=True) \
        .range(skip, skip + limit - 1) \
        .execute()
    
    if not participations.data:
        return []
    
    result = []
    challenge_ids = [p["challenge_id"] for p in participations.data]
    
    for challenge_id in challenge_ids:
        # Get challenge data
        challenge_data = db.table("challenges").select("*").eq("id", challenge_id).execute()
        
        if not challenge_data.data or len(challenge_data.data) == 0:
            continue
        
        challenge = challenge_data.data[0]
        
        # Skip private challenges if current user is not the creator
        if challenge["is_private"] and (not current_user or str(current_user.id) != challenge["creator_id"]):
            # Unless they're a participant
            if current_user:
                participant = db.table("challenge_participants") \
                    .select("*") \
                    .eq("challenge_id", challenge["id"]) \
                    .eq("user_id", str(current_user.id)) \
                    .execute()
                
                if not participant.data or len(participant.data) == 0:
                    continue
            else:
                continue
        
        # Get creator data
        creator_data = db.table("users").select("*").eq("id", challenge["creator_id"]).execute()
        
        if creator_data.data and len(creator_data.data) > 0:
            creator = creator_data.data[0]
        else:
            creator = None
        
        # Get participants count
        participants_count = db.table("challenge_participants") \
            .select("user_id", count="exact") \
            .eq("challenge_id", challenge["id"]) \
            .execute()
        
        # Get posts count
        posts_count = db.table("challenge_posts") \
            .select("post_id", count="exact") \
            .eq("challenge_id", challenge["id"]) \
            .execute()
        
        # Check if current user is joined
        is_joined = False
        if current_user:
            joined = db.table("challenge_participants") \
                .select("*") \
                .eq("challenge_id", challenge["id"]) \
                .eq("user_id", str(current_user.id)) \
                .execute()
            
            is_joined = joined.data and len(joined.data) > 0
        
        challenge_with_details = {
            **challenge,
            "creator": creator,
            "participant_count": participants_count.count if hasattr(participants_count, 'count') else 0,
            "posts_count": posts_count.count if hasattr(posts_count, 'count') else 0,
            "is_joined": is_joined,
        }
        
        result.append(challenge_with_details)
    
    return result 