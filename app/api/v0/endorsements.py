import random
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import supabase
from app.core.deps import get_current_user, get_supabase
from app.schemas.endorsements import (EndorsementCreate, EndorsementOut,
                                      EndorsementUpdate)
from app.schemas.notifications import NotificationType

router = APIRouter(tags=["endorsements"])

@router.post(
    "/",
    response_model=List[EndorsementOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create endorsement requests for a post",
)
def request_endorsements(
    post_id: str,
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """
    Create endorsement requests for a post by randomly selecting 3 of the user's friends.
    
    Args:
        post_id (str): UUID of the post to be endorsed
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        
    Returns:
        List[EndorsementOut]: The created endorsement requests
        
    Raises:
        HTTPException: 400 if there are no friends or user is not post owner
        HTTPException: 404 if post not found
    """
    try:
        # Check if post exists and belongs to current user
        post = supabase.table("posts").select("*").eq("id", post_id).execute()
        
        if not post.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
            
        if post.data[0]["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the post owner can request endorsements"
            )
            
        # Get user's friends (people the user follows AND who follow the user back)
        follows_query = supabase.table("follows").select("followed_id").eq("follower_id", current_user.id).execute()
        following_ids = [follow["followed_id"] for follow in follows_query.data]
        
        if not following_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You need to have friends to request endorsements"
            )
            
        # Find mutual follows (friends)
        followers_query = supabase.table("follows").select("follower_id").eq("followed_id", current_user.id)\
            .in_("follower_id", following_ids).execute()
        
        friends = [follow["follower_id"] for follow in followers_query.data]
        
        if len(friends) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You need at least 3 mutual friends to use endorsements"
            )
        
        # Randomly select 3 friends to endorse
        selected_friends = random.sample(friends, 3)
        
        # Create endorsement requests
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        endorsements = []
        
        for friend_id in selected_friends:
            endorsement_data = {
                "post_id": post_id,
                "endorser_id": friend_id,
                "status": "pending",
                "created_at": now
            }
            
            # Check if an endorsement request already exists
            existing = supabase.table("post_endorsements")\
                .select("*")\
                .eq("post_id", post_id)\
                .eq("endorser_id", friend_id)\
                .execute()
                
            if existing.data:
                endorsements.append(existing.data[0])
                continue
                
            # Insert new endorsement request
            result = supabase.table("post_endorsements").insert(endorsement_data).execute()
            endorsements.append(result.data[0])
            
            # Create notification for the endorser
            notification_data = {
                "type": "endorsement_request",
                "user_id": friend_id,
                "triggered_by_user_id": current_user.id,
                "post_id": post_id,
                "message": f"{current_user.username} has requested your endorsement on their post",
                "is_read": False,
                "created_at": now,
                "status": "pending"
            }
            
            supabase.table("notifications").insert(notification_data).execute()
        
        return endorsements
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating endorsement requests: {str(e)}"
        )

@router.get(
    "/post/{post_id}",
    response_model=List[EndorsementOut],
    summary="Get all endorsements for a post",
)
def get_post_endorsements(
    post_id: str,
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """
    Get all endorsements for a specific post.
    
    Args:
        post_id (str): UUID of the post
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        
    Returns:
        List[EndorsementOut]: List of endorsements for the post
    """
    try:
        # Check if post exists and belongs to current user or user is an endorser
        post = supabase.table("posts").select("user_id").eq("id", post_id).execute()
        
        if not post.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
            
        # Get all endorsements for the post
        endorsements = supabase.table("post_endorsements")\
            .select("*")\
            .eq("post_id", post_id)\
            .execute()
            
        return endorsements.data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error fetching endorsements: {str(e)}"
        )

@router.get(
    "/pending",
    response_model=List[EndorsementOut],
    summary="Get your pending endorsement requests",
)
def get_pending_endorsements(
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """
    Get all pending endorsement requests for the current user.
    
    Args:
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        
    Returns:
        List[EndorsementOut]: List of pending endorsements
    """
    try:
        endorsements = supabase.table("post_endorsements")\
            .select("*")\
            .eq("endorser_id", current_user.id)\
            .eq("status", "pending")\
            .execute()
            
        return endorsements.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error fetching pending endorsements: {str(e)}"
        )

@router.put(
    "/{endorsement_id}",
    response_model=EndorsementOut,
    summary="Update an endorsement (endorse or decline)",
)
def update_endorsement(
    endorsement_id: str,
    payload: EndorsementUpdate,
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """
    Update an endorsement status (endorse or decline).
    
    Args:
        endorsement_id (str): UUID of the endorsement to update
        payload (EndorsementUpdate): Updated endorsement data
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        
    Returns:
        EndorsementOut: The updated endorsement
        
    Raises:
        HTTPException: 403 if user is not the endorser
        HTTPException: 404 if endorsement not found
    """
    try:
        # Check if endorsement exists and belongs to current user
        endorsement = supabase.table("post_endorsements")\
            .select("*")\
            .eq("id", endorsement_id)\
            .execute()
            
        if not endorsement.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
            
        if endorsement.data[0]["endorser_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the endorser can update this endorsement"
            )
            
        # Prepare update data
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")
        update_data = {
            "status": payload.status,
        }
        
        # If status is 'endorsed', add selfie URL and endorsed_at timestamp
        if payload.status == "endorsed":
            if not payload.selfie_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selfie URL is required for endorsement"
                )
                
            update_data["selfie_url"] = payload.selfie_url
            update_data["endorsed_at"] = now
            
        # Update the endorsement
        result = supabase.table("post_endorsements")\
            .update(update_data)\
            .eq("id", endorsement_id)\
            .execute()
            
        updated_endorsement = result.data[0]
        
        # If the endorsement was approved, check if all 3 endorsements are complete
        if payload.status == "endorsed":
            post_id = endorsement.data[0]["post_id"]
            
            # Get all endorsements for the post
            all_endorsements = supabase.table("post_endorsements")\
                .select("*")\
                .eq("post_id", post_id)\
                .execute()
                
            # Check if all required endorsements are complete
            endorsed_count = sum(1 for e in all_endorsements.data if e["status"] == "endorsed")
            
            if endorsed_count >= 3:
                # Update post to mark as endorsed
                supabase.table("posts")\
                    .update({"is_endorsed": True})\
                    .eq("id", post_id)\
                    .execute()
                    
                # Get post owner to send notification
                post = supabase.table("posts").select("user_id").eq("id", post_id).execute()
                post_owner_id = post.data[0]["user_id"]
                
                # Send notification to post owner
                notification_data = {
                    "type": "post_endorsed",
                    "user_id": post_owner_id,
                    "triggered_by_user_id": current_user.id,
                    "post_id": post_id,
                    "message": "Your post has been fully endorsed!",
                    "is_read": False,
                    "created_at": now,
                    "status": "pending"
                }
                
                supabase.table("notifications").insert(notification_data).execute()
                
        return updated_endorsement
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating endorsement: {str(e)}"
        ) 