import random
from datetime import datetime
from typing import List, Optional

from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                     status)

from app.core.config import supabase
from app.core.deps import get_current_user, get_supabase
from app.core.media import delete_file, upload_base64_image, upload_file
from app.schemas.endorsements import (EndorsementCreate, EndorsementOut,
                                      EndorsementStatus, EndorsementUpdate)
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
async def update_endorsement(
    endorsement_id: str,
    status: EndorsementStatus = Form(...),
    selfie: Optional[UploadFile] = File(None),
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """
    Update an endorsement status (endorse or decline) with selfie.
    
    Args:
        endorsement_id (str): UUID of the endorsement to update
        status (EndorsementStatus): New status of the endorsement
        selfie (UploadFile, optional): Selfie image for endorsement verification
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        
    Returns:
        EndorsementOut: The updated endorsement
        
    Raises:
        HTTPException: 400 if no selfie provided with "endorsed" status
        HTTPException: 403 if user is not the endorser
        HTTPException: 404 if endorsement not found
    """
    try:
        # Check if endorsement exists and belongs to current user
        endorsement_resp = supabase.table("post_endorsements")\
            .select("*, post_id(user_id)")\
            .eq("id", endorsement_id)\
            .single()\
            .execute()
            
        if not endorsement_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
        
        existing_endorsement = endorsement_resp.data
        original_post_owner_id = existing_endorsement.get("post_id", {}).get("user_id") # post_id is a dict here

        if existing_endorsement["endorser_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this endorsement"
            )

        if status == EndorsementStatus.ENDORSED and not selfie:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selfie is required to endorse."
            )

        update_data = {"status": status.value}
        new_selfie_data_to_store = existing_endorsement.get("selfie_url") # Default to existing

        # Handle selfie upload and old selfie deletion
        old_selfie_db_value = existing_endorsement.get("selfie_url")

        if selfie: # New selfie provided
            if old_selfie_db_value and isinstance(old_selfie_db_value, list) and len(old_selfie_db_value) == 2:
                try:
                    delete_file(bucket_name=old_selfie_db_value[0], file_path=old_selfie_db_value[1])
                except Exception as e_del:
                    print(f"Error deleting old selfie {old_selfie_db_value}: {e_del}") # Log error
            
            uploaded_filename = await upload_file("selfie_url", selfie, current_user.id) # Use "selfie_url" bucket
            new_selfie_data_to_store = ["selfie_url", uploaded_filename]
        
        elif status == EndorsementStatus.DECLINED: # No new selfie, and status is declined
            if old_selfie_db_value and isinstance(old_selfie_db_value, list) and len(old_selfie_db_value) == 2:
                try:
                    delete_file(bucket_name=old_selfie_db_value[0], file_path=old_selfie_db_value[1])
                except Exception as e_del:
                    print(f"Error deleting selfie on decline {old_selfie_db_value}: {e_del}") # Log error
            new_selfie_data_to_store = None
        
        update_data["selfie_url"] = new_selfie_data_to_store
        update_data["endorsed_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f") if status == EndorsementStatus.ENDORSED else None

        # Update the endorsement
        updated_endorsement_resp = supabase.table("post_endorsements")\
            .update(update_data)\
            .eq("id", endorsement_id)\
            .execute()
       
        # Fetch the fully updated endorsement to return
        final_endorsement = supabase.table("post_endorsements")\
            .select("*")\
            .eq("id", endorsement_id)\
            .single()\
            .execute()

        return final_endorsement.data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating endorsement: {str(e)}"
        )

@router.post(
    "/{endorsement_id}/selfie",
    response_model=EndorsementOut,
    summary="Upload a selfie for an endorsement",
)
async def upload_endorsement_selfie(
    endorsement_id: str,
    selfie: UploadFile = File(...),
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """
    Upload a selfie for an endorsement.
    
    Args:
        endorsement_id (str): UUID of the endorsement
        selfie (UploadFile): Selfie image file
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
        endorsement_resp = supabase.table("post_endorsements")\
            .select("*")\
            .eq("id", endorsement_id)\
            .single()\
            .execute()
            
        if not endorsement_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
        
        existing_endorsement_data = endorsement_resp.data

        if existing_endorsement_data["endorser_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the endorser can upload a selfie for this endorsement"
            )
            
        # Delete old selfie if it exists
        old_selfie_db_value = existing_endorsement_data.get("selfie_url")
        if old_selfie_db_value and isinstance(old_selfie_db_value, list) and len(old_selfie_db_value) == 2:
            try:
                delete_file(bucket_name=old_selfie_db_value[0], file_path=old_selfie_db_value[1])
            except Exception as e:
                print(f"Failed to delete old selfie {old_selfie_db_value}: {str(e)}") # Log error
                
        # Upload new selfie to "selfie_url" bucket, keeping folder structure if intended
        uploaded_filename = await upload_file("selfie_url", selfie, current_user.id, folder=endorsement_id)
        new_selfie_to_store = ["selfie_url", uploaded_filename]
        
        # Update endorsement
        supabase.table("post_endorsements")\
            .update({"selfie_url": new_selfie_to_store})\
            .eq("id", endorsement_id)\
            .execute()
            
        # Fetch and return the updated endorsement object to use EndorsementOut model
        updated_record = supabase.table("post_endorsements").select("*").eq("id", endorsement_id).single().execute()
        return updated_record.data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading selfie: {str(e)}"
        )

@router.post(
    "/{endorsement_id}/selfie/base64",
    response_model=EndorsementOut,
    summary="Upload a base64 encoded selfie for an endorsement",
)
async def upload_endorsement_selfie_base64(
    endorsement_id: str,
    base64_image: str = Form(...),
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """
    Upload a base64 encoded selfie for an endorsement.
    
    Args:
        endorsement_id (str): UUID of the endorsement
        base64_image (str): Base64 encoded image data
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
        endorsement_resp = supabase.table("post_endorsements")\
            .select("*")\
            .eq("id", endorsement_id)\
            .single()\
            .execute()
            
        if not endorsement_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
        
        existing_endorsement_data = endorsement_resp.data

        if existing_endorsement_data["endorser_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the endorser can upload a selfie for this endorsement"
            )
            
        # Delete old selfie if it exists
        old_selfie_db_value = existing_endorsement_data.get("selfie_url")
        if old_selfie_db_value and isinstance(old_selfie_db_value, list) and len(old_selfie_db_value) == 2:
            try:
                delete_file(bucket_name=old_selfie_db_value[0], file_path=old_selfie_db_value[1])
            except Exception as e:
                print(f"Failed to delete old selfie {old_selfie_db_value}: {str(e)}") # Log error
                
        # Upload new selfie to "selfie_url" bucket, keeping folder structure if intended
        uploaded_filename = await upload_base64_image("selfie_url", base64_image, current_user.id, folder=endorsement_id)
        new_selfie_to_store = ["selfie_url", uploaded_filename]
        
        # Update endorsement
        supabase.table("post_endorsements")\
            .update({"selfie_url": new_selfie_to_store})\
            .eq("id", endorsement_id)\
            .execute()
            
        # Fetch and return the updated endorsement object to use EndorsementOut model
        updated_record = supabase.table("post_endorsements").select("*").eq("id", endorsement_id).single().execute()
        return updated_record.data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading selfie: {str(e)}"
        ) 