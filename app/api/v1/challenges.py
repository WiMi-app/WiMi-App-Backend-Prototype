from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.core.deps import get_current_active_user
from app.db.database import get_supabase
from app.schemas.challenges import Challenge, ChallengeCreate, ChallengeUpdate, ChallengeWithDetails
from app.schemas.challenges import ChallengeParticipant, ChallengeParticipantCreate
from app.schemas.challenges import ChallengePost, ChallengePostCreate, ChallengeAchievement
from app.schemas.users import User

router = APIRouter()


@router.post("/", response_model=Challenge)
def create_challenge(
    challenge_data: ChallengeCreate,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Create a new challenge.
    """
    now = datetime.now().isoformat()
    challenge_dict = challenge_data.model_dump_json_safe()
    
    # Handle None values for optional fields
    if challenge_dict.get("check_in_time") is not None:
        challenge_dict["check_in_time"] = challenge_dict["check_in_time"].isoformat()
    
    challenge_dict.update({
        "creator_id": str(current_user.id),
        "created_at": now,
        "updated_at": now,
    })
    
    result = db.table("challenges").insert(challenge_dict).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create challenge",
        )
    
    return Challenge(**result.data[0])


@router.get("/", response_model=List[ChallengeWithDetails])
def get_challenges(
    skip: int = 0,
    limit: int = 10,
    creator_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    db: Client = Depends(get_supabase),
    current_user: Optional[User] = Depends(get_current_active_user),
) -> Any:
    """
    Get all challenges with optional filtering.
    """
    query = db.table("challenges") \
        .select("*") \
        .order("created_at", desc=True)
    
    # Apply filters
    if creator_id:
        query = query.eq("creator_id", str(creator_id))
    
    if is_active is not None:
        query = query.eq("is_active", is_active)
    
    # Only show private challenges if user is the creator or a participant
    if current_user:
        # Complex query: show public challenges OR private ones where the user is creator/participant
        # This is a simplified approach for Supabase
        challenges = query.range(skip, skip + limit - 1).execute()
        
        if not challenges.data:
            return []
        
        filtered_challenges = []
        for challenge in challenges.data:
            # If challenge is public or user is creator, include it
            if not challenge["is_private"] or challenge["creator_id"] == str(current_user.id):
                filtered_challenges.append(challenge)
            else:
                # Check if user is a participant
                participant = db.table("challenge_participants") \
                    .select("*") \
                    .eq("challenge_id", challenge["id"]) \
                    .eq("user_id", str(current_user.id)) \
                    .execute()
                
                if participant.data and len(participant.data) > 0:
                    filtered_challenges.append(challenge)
    else:
        # No user, only show public challenges
        challenges = query.eq("is_private", False).range(skip, skip + limit - 1).execute()
        filtered_challenges = challenges.data if challenges.data else []
    
    result = []
    
    for challenge in filtered_challenges:
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


@router.get("/{challenge_id}", response_model=ChallengeWithDetails)
def get_challenge(
    challenge_id: UUID,
    db: Client = Depends(get_supabase),
    current_user: Optional[User] = Depends(get_current_active_user),
) -> Any:
    """
    Get a specific challenge by ID.
    """
    challenge_data = db.table("challenges").select("*").eq("id", str(challenge_id)).execute()
    
    if not challenge_data.data or len(challenge_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {challenge_id} not found",
        )
    
    challenge = challenge_data.data[0]
    
    # Check access for private challenges
    if challenge["is_private"] and (not current_user or challenge["creator_id"] != str(current_user.id)):
        # Check if user is a participant
        if current_user:
            participant = db.table("challenge_participants") \
                .select("*") \
                .eq("challenge_id", challenge["id"]) \
                .eq("user_id", str(current_user.id)) \
                .execute()
            
            if not participant.data or len(participant.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view this private challenge",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this private challenge",
            )
    
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
        "posts_count": posts_count.count if hasattr(posts_count, 'count') 
        else 0,
        "is_joined": is_joined,
    }
    
    return challenge_with_details


@router.put("/{challenge_id}", response_model=Challenge)
def update_challenge(
    challenge_id: UUID,
    challenge_update: ChallengeUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Update a specific challenge.
    """
    challenge_data = db.table("challenges").select("*").eq("id", str(challenge_id)).execute()
    
    if not challenge_data.data or len(challenge_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {challenge_id} not found",
        )
    
    challenge = challenge_data.data[0]
    
    # Check if user is the creator
    if challenge["creator_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this challenge",
        )
    
    update_data = {key: value for key, value in challenge_update.dict().items() if value is not None}
    
    # Handle time field formatting
    if "check_in_time" in update_data and update_data["check_in_time"] is not None:
        update_data["check_in_time"] = update_data["check_in_time"].isoformat()
    
    update_data["updated_at"] = datetime.now().isoformat()
    
    result = db.table("challenges") \
        .update(update_data) \
        .eq("id", str(challenge_id)) \
        .execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update challenge",
        )
    
    return Challenge(**result.data[0])


@router.delete("/{challenge_id}", response_model=dict)
def delete_challenge(
    challenge_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Delete a specific challenge.
    """
    challenge_data = db.table("challenges").select("*").eq("id", str(challenge_id)).execute()
    
    if not challenge_data.data or len(challenge_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {challenge_id} not found",
        )
    
    challenge = challenge_data.data[0]
    
    # Check if user is the creator
    if challenge["creator_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this challenge",
        )
    
    # Delete the challenge (cascade should handle related records)
    db.table("challenges").delete().eq("id", str(challenge_id)).execute()
    
    return {"message": "Challenge deleted successfully"}


@router.post("/join", response_model=ChallengeParticipant)
def join_challenge(
    join_data: ChallengeParticipantCreate,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Join a challenge.
    """
    challenge_id = join_data.challenge_id
    
    # Check if challenge exists
    challenge_data = db.table("challenges").select("*").eq("id", str(challenge_id)).execute()
    
    if not challenge_data.data or len(challenge_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {challenge_id} not found",
        )
    
    challenge = challenge_data.data[0]
    
    # Check if user is already a participant
    existing = db.table("challenge_participants") \
        .select("*") \
        .eq("challenge_id", str(challenge_id)) \
        .eq("user_id", str(current_user.id)) \
        .execute()
    
    if existing.data and len(existing.data) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already participating in this challenge",
        )
    
    # Check max participants limit
    if challenge["max_participants"]:
        participants_count = db.table("challenge_participants") \
            .select("user_id", count="exact") \
            .eq("challenge_id", str(challenge_id)) \
            .execute()
        
        count = participants_count.count if hasattr(participants_count, 'count') else 0
        
        if count >= challenge["max_participants"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This challenge has reached its maximum number of participants",
            )
    
    # Add user as participant
    now = datetime.now().isoformat()
    participant_data = {
        "challenge_id": str(challenge_id),
        "user_id": str(current_user.id),
        "joined_at": now,
        "status": "active",
    }
    
    result = db.table("challenge_participants").insert(participant_data).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join challenge",
        )
    
    return ChallengeParticipant(**result.data[0])


@router.delete("/leave/{challenge_id}", response_model=dict)
def leave_challenge(
    challenge_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Leave a challenge.
    """
    # Check if challenge exists
    challenge_data = db.table("challenges").select("*").eq("id", str(challenge_id)).execute()
    
    if not challenge_data.data or len(challenge_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {challenge_id} not found",
        )
    
    # Check if user is a participant
    participant = db.table("challenge_participants") \
        .select("*") \
        .eq("challenge_id", str(challenge_id)) \
        .eq("user_id", str(current_user.id)) \
        .execute()
    
    if not participant.data or len(participant.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not participating in this challenge",
        )
    
    # Remove user from challenge
    db.table("challenge_participants") \
        .delete() \
        .eq("challenge_id", str(challenge_id)) \
        .eq("user_id", str(current_user.id)) \
        .execute()
    
    return {"message": "You have left the challenge successfully"}


@router.post("/post", response_model=ChallengePost)
def add_post_to_challenge(
    post_data: ChallengePostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Add a post to a challenge (can be a check-in or a regular post).
    """
    challenge_id = post_data.challenge_id
    post_id = post_data.post_id
    
    # Check if challenge exists
    challenge_data = db.table("challenges").select("*").eq("id", str(challenge_id)).execute()
    
    if not challenge_data.data or len(challenge_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {challenge_id} not found",
        )
    
    # Check if post exists and belongs to the current user
    post_data = db.table("posts").select("*").eq("id", str(post_id)).execute()
    
    if not post_data.data or len(post_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {post_id} not found",
        )
    
    post = post_data.data[0]
    
    if post["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add your own posts to a challenge",
        )
    
    # Check if post is already added to the challenge
    existing = db.table("challenge_posts") \
        .select("*") \
        .eq("challenge_id", str(challenge_id)) \
        .eq("post_id", str(post_id)) \
        .execute()
    
    if existing.data and len(existing.data) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This post is already added to the challenge",
        )
    
    # Add post to challenge
    now = datetime.now().isoformat()
    challenge_post_data = {
        "challenge_id": str(challenge_id),
        "post_id": str(post_id),
        "is_check_in": post_data.is_check_in,
        "submitted_at": now,
    }
    
    result = db.table("challenge_posts").insert(challenge_post_data).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add post to challenge",
        )
    
    # Check if this is a check-in for a streak calculation
    if post_data.is_check_in:
        # A simple streak calculation could be added here
        # This is a placeholder for more complex streak logic
        pass
    
    return ChallengePost(**result.data[0])


@router.get("/{challenge_id}/posts", response_model=List[dict])
def get_challenge_posts(
    challenge_id: UUID,
    skip: int = 0,
    limit: int = 10,
    db: Client = Depends(get_supabase),
    current_user: Optional[User] = Depends(get_current_active_user),
) -> Any:
    """
    Get all posts for a specific challenge.
    """
    # Check if challenge exists and user has access
    challenge_data = db.table("challenges").select("*").eq("id", str(challenge_id)).execute()
    
    if not challenge_data.data or len(challenge_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {challenge_id} not found",
        )
    
    challenge = challenge_data.data[0]
    
    # Check access for private challenges
    if challenge["is_private"] and (not current_user or challenge["creator_id"] != str(current_user.id)):
        # Check if user is a participant
        if current_user:
            participant = db.table("challenge_participants") \
                .select("*") \
                .eq("challenge_id", challenge["id"]) \
                .eq("user_id", str(current_user.id)) \
                .execute()
            
            if not participant.data or len(participant.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view posts for this private challenge",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view posts for this private challenge",
            )
    
    # Get challenge posts
    challenge_posts = db.table("challenge_posts") \
        .select("*") \
        .eq("challenge_id", str(challenge_id)) \
        .order("submitted_at", desc=True) \
        .range(skip, skip + limit - 1) \
        .execute()
    
    if not challenge_posts.data:
        return []
    
    result = []
    
    for cp in challenge_posts.data:
        # Get the post
        post_data = db.table("posts").select("*").eq("id", cp["post_id"]).execute()
        
        if post_data.data and len(post_data.data) > 0:
            post = post_data.data[0]
            
            # Get the user
            user_data = db.table("users").select("*").eq("id", post["user_id"]).execute()
            
            if user_data.data and len(user_data.data) > 0:
                user = user_data.data[0]
            else:
                user = None
            
            # Get comments count
            comments_count = db.table("comments").select("id", count="exact").eq("post_id", post["id"]).execute()
            
            # Get likes count
            likes_count = db.table("likes").select("id", count="exact").eq("post_id", post["id"]).execute()
            
            post_with_details = {
                **post,
                "user": user,
                "comments_count": comments_count.count if hasattr(comments_count, 'count') else 0,
                "likes_count": likes_count.count if hasattr(likes_count, 'count') else 0,
                "challenge_post_details": cp,
            }
            
            result.append(post_with_details)
    
    return result


@router.get("/{challenge_id}/participants", response_model=List[dict])
def get_challenge_participants(
    challenge_id: UUID,
    skip: int = 0,
    limit: int = 10,
    db: Client = Depends(get_supabase),
    current_user: Optional[User] = Depends(get_current_active_user),
) -> Any:
    """
    Get all participants for a specific challenge.
    """
    # Check if challenge exists and user has access
    challenge_data = db.table("challenges").select("*").eq("id", str(challenge_id)).execute()
    
    if not challenge_data.data or len(challenge_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {challenge_id} not found",
        )
    
    challenge = challenge_data.data[0]
    
    # Check access for private challenges
    if challenge["is_private"] and (not current_user or challenge["creator_id"] != str(current_user.id)):
        # Check if user is a participant
        if current_user:
            participant = db.table("challenge_participants") \
                .select("*") \
                .eq("challenge_id", challenge["id"]) \
                .eq("user_id", str(current_user.id)) \
                .execute()
            
            if not participant.data or len(participant.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view participants for this private challenge",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view participants for this private challenge",
            )
    
    # Get challenge participants
    participants = db.table("challenge_participants") \
        .select("*") \
        .eq("challenge_id", str(challenge_id)) \
        .order("joined_at", desc=True) \
        .range(skip, skip + limit - 1) \
        .execute()
    
    if not participants.data:
        return []
    
    result = []
    
    for participant in participants.data:
        # Get the user
        user_data = db.table("users").select("*").eq("id", participant["user_id"]).execute()
        
        if user_data.data and len(user_data.data) > 0:
            user = user_data.data[0]
            
            # Get participant's check-ins count
            checkins = db.table("challenge_posts") \
                .select("post_id", count="exact") \
                .eq("challenge_id", str(challenge_id)) \
                .eq("is_check_in", True) \
                .execute()
            
            # Join with posts to filter by user
            # This is simplified - in a real app, you'd need a more complex join
            user_checkins = 0
            if checkins.data:
                for post_id in [c["post_id"] for c in checkins.data]:
                    post = db.table("posts").select("user_id").eq("id", post_id).execute()
                    if post.data and len(post.data) > 0 and post.data[0]["user_id"] == participant["user_id"]:
                        user_checkins += 1
            
            participant_with_details = {
                **participant,
                "user": user,
                "checkins_count": user_checkins,
            }
            
            result.append(participant_with_details)
    
    return result


@router.get("/search", response_model=List[ChallengeWithDetails])
def search_challenges(
    query: str,
    skip: int = 0,
    limit: int = 10,
    db: Client = Depends(get_supabase),
    current_user: Optional[User] = Depends(get_current_active_user),
) -> Any:
    """
    Search for challenges by title or description.
    """
    # Simple text search - Supabase offers more advanced full-text search capabilities
    # This is a simplified approach that searches for title or description containing the query
    challenges_query = db.table("challenges") \
        .select("*") \
        .order("created_at", desc=True)
    
    # Execute the query
    challenges = challenges_query.execute()
    
    if not challenges.data:
        return []
    
    # Filter results client-side for simple text matching
    # This is not ideal for large datasets but works for demonstration
    filtered_challenges = []
    query = query.lower()
    
    for challenge in challenges.data:
        title = challenge.get("title", "").lower()
        description = challenge.get("description", "").lower() if challenge.get("description") else ""
        
        if query in title or query in description:
            # If challenge is private, only show if user is the creator or a participant
            if challenge["is_private"]:
                if not current_user:
                    continue
                    
                if challenge["creator_id"] != str(current_user.id):
                    # Check if user is a participant
                    participant = db.table("challenge_participants") \
                        .select("*") \
                        .eq("challenge_id", challenge["id"]) \
                        .eq("user_id", str(current_user.id)) \
                        .execute()
                    
                    if not participant.data or len(participant.data) == 0:
                        continue
            
            filtered_challenges.append(challenge)
    
    # Apply pagination
    paginated_challenges = filtered_challenges[skip:skip + limit]
    
    result = []
    
    for challenge in paginated_challenges:
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


@router.get("/trending", response_model=List[ChallengeWithDetails])
def get_trending_challenges(
    time_period: Optional[str] = "week",  # "day", "week", "month"
    limit: int = 10,
    db: Client = Depends(get_supabase),
    current_user: Optional[User] = Depends(get_current_active_user),
) -> Any:
    """
    Get trending challenges based on recent participation and activity.
    """
    # Get all active challenges
    challenges_query = db.table("challenges") \
        .select("*") \
        .eq("is_active", True)
    
    if not current_user:
        # Only include public challenges for non-authenticated users
        challenges_query = challenges_query.eq("is_private", False)
    
    challenges = challenges_query.execute()
    
    if not challenges.data:
        return []
    
    # Calculate trending score for each challenge
    trending_challenges = []
    
    for challenge in challenges.data:
        # Skip private challenges if user is not the creator or participant
        if challenge["is_private"] and current_user and challenge["creator_id"] != str(current_user.id):
            # Check if user is a participant
            participant = db.table("challenge_participants") \
                .select("*") \
                .eq("challenge_id", challenge["id"]) \
                .eq("user_id", str(current_user.id)) \
                .execute()
            
            if not participant.data or len(participant.data) == 0:
                continue
        
        # Get recent participants count
        from_date = datetime.now()
        if time_period == "day":
            from_date = (from_date - datetime.timedelta(days=1))
        elif time_period == "week":
            from_date = (from_date - datetime.timedelta(weeks=1))
        elif time_period == "month":
            from_date = (from_date - datetime.timedelta(days=30))
        
        # Count recent participants (simplified as Supabase filter capabilities vary)
        participants_all = db.table("challenge_participants") \
            .select("*") \
            .eq("challenge_id", challenge["id"]) \
            .execute()
        
        recent_participants = 0
        if participants_all.data:
            recent_participants = sum(1 for p in participants_all.data if p["joined_at"] > from_date.isoformat())
        
        # Count recent posts
        posts_all = db.table("challenge_posts") \
            .select("*") \
            .eq("challenge_id", challenge["id"]) \
            .execute()
        
        recent_posts = 0
        if posts_all.data:
            recent_posts = sum(1 for p in posts_all.data if p["submitted_at"] > from_date.isoformat())
        
        # Calculate trending score (simple algorithm - can be refined)
        trend_score = (recent_participants * 3) + recent_posts
        
        if trend_score > 0:
            trending_challenges.append((challenge, trend_score))
    
    # Sort by trend score and limit results
    trending_challenges.sort(key=lambda x: x[1], reverse=True)
    top_challenges = [c[0] for c in trending_challenges[:limit]]
    
    result = []
    
    for challenge in top_challenges:
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


@router.put("/participant/status", response_model=ChallengeParticipant)
def update_participant_status(
    challenge_id: UUID,
    status: str,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Update the status of a challenge participant (active, completed, dropped).
    """
    # Check if challenge exists
    challenge_data = db.table("challenges").select("*").eq("id", str(challenge_id)).execute()
    
    if not challenge_data.data or len(challenge_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {challenge_id} not found",
        )
    
    # Check if user is a participant
    participant = db.table("challenge_participants") \
        .select("*") \
        .eq("challenge_id", str(challenge_id)) \
        .eq("user_id", str(current_user.id)) \
        .execute()
    
    if not participant.data or len(participant.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not participating in this challenge",
        )
    
    # Validate status
    valid_statuses = ["active", "completed", "dropped"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )
    
    # Update participant status
    result = db.table("challenge_participants") \
        .update({"status": status}) \
        .eq("challenge_id", str(challenge_id)) \
        .eq("user_id", str(current_user.id)) \
        .execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update participant status",
        )
    
    # If status is completed, create an achievement
    if status == "completed":
        # Get challenge data to use its title
        challenge_data = db.table("challenges").select("*").eq("id", str(challenge_id)).execute()
        if not challenge_data.data or len(challenge_data.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Challenge with ID {challenge_id} not found",
            )
        challenge = challenge_data.data[0]
        
        now = datetime.now().isoformat()
        achievement_data = {
            "challenge_id": str(challenge_id),
            "user_id": str(current_user.id),
            "achievement_type": "completion",
            "description": f"Completed the challenge: {challenge['title']}",
            "achieved_at": now,
        }
        
        db.table("challenge_achievements").insert(achievement_data).execute()
        
        # Create notification for achievement
        notification_dict = {
            "user_id": str(current_user.id),
            "triggered_by_user_id": str(current_user.id),  # Self-triggered
            "challenge_id": str(challenge_id),
            "type": "achievement",
            "message": f"Congratulations! You completed the challenge: {challenge['title']}",
            "created_at": now,
        }
        
        db.table("notifications").insert(notification_dict).execute()
    
    return ChallengeParticipant(**result.data[0])


@router.get("/achievements", response_model=List[ChallengeAchievement])
def get_user_achievements(
    user_id: Optional[UUID] = None,
    challenge_id: Optional[UUID] = None,
    db: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get a user's achievements, optionally filtered by challenge.
    If no user_id is provided, returns achievements for the current user.
    """
    query = db.table("challenge_achievements").select("*")
    
    # Filter by user
    target_user_id = user_id if user_id else current_user.id
    query = query.eq("user_id", str(target_user_id))
    
    # Filter by challenge if specified
    if challenge_id:
        query = query.eq("challenge_id", str(challenge_id))
    
    # Execute query
    achievements = query.order("achieved_at", desc=True).execute()
    
    if not achievements.data:
        return []
    
    return [ChallengeAchievement(**achievement) for achievement in achievements.data]


@router.post("/achievement", response_model=ChallengeAchievement)
def add_achievement(
    challenge_id: UUID,
    achievement_type: str,
    description: str,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Add a new achievement for a user in a specific challenge.
    """
    # Check if challenge exists
    challenge_data = db.table("challenges").select("*").eq("id", str(challenge_id)).execute()
    
    if not challenge_data.data or len(challenge_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {challenge_id} not found",
        )
    
    challenge = challenge_data.data[0]
    
    # Check if user is the creator
    if challenge["creator_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add an achievement to this challenge",
        )
    
    # Create achievement
    now = datetime.now().isoformat()
    achievement_data = {
        "challenge_id": str(challenge_id),
        "user_id": str(current_user.id),
        "achievement_type": achievement_type,
        "description": description,
        "achieved_at": now,
    }
    
    result = db.table("challenge_achievements").insert(achievement_data).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add achievement",
        )
    
    return ChallengeAchievement(**result.data[0])


@router.delete("/achievement", response_model=dict)
def delete_achievement(
    achievement_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Delete an achievement for a user.
    """
    # Check if achievement exists
    achievement_data = db.table("challenge_achievements").select("*").eq("id", str(achievement_id)).execute()
    
    if not achievement_data.data or len(achievement_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Achievement with ID {achievement_id} not found",
        )
    
    achievement = achievement_data.data[0]
    
    # Check if user is the creator
    if achievement["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this achievement",
        )
    
    # Delete the achievement
    db.table("challenge_achievements").delete().eq("id", str(achievement_id)).execute()
    
    return {"message": "Achievement deleted successfully"} 