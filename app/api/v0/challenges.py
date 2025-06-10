"""
Challenges API endpoints for managing challenge resources.
Provides CRUD operations for challenges with authorization controls.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import supabase
from app.core.deps import get_current_user, get_supabase
from app.core.media import delete_file, upload_file, upload_base64_image
from app.core.moderation import moderate_challenge
from app.schemas.challenges import (ChallengeCreate, ChallengeOut,
                                    ChallengeParticipantOut, ChallengeUpdate,
                                    ParticipationStatus)
from app.schemas.posts import PostOut
from app.schemas.base64 import Base64Images

router = APIRouter(tags=["challenges"])

@router.post("/", response_model=ChallengeOut, status_code=status.HTTP_201_CREATED)
async def create_challenge(payload: ChallengeCreate, user=Depends(get_current_user)):
    """
    Create a new challenge.
    
    Args:
        payload (ChallengeCreate): Challenge data to create
        user: Current authenticated user from token
        
    Returns:
        ChallengeOut: Created challenge data
        
    Raises:
        HTTPException: 400 if creation fails or content is flagged
        HTTPException: 403 if content violates moderation policy
    """
    try:
        if payload.description:
            await moderate_challenge(payload.description, raise_exception=True)
        
        record = payload.model_dump()
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        record.update({"creator_id": user.id, "created_at": now, "updated_at": now})
        
        if "check_in_time" in record and record["check_in_time"] is not None:
            record["check_in_time"] = record["check_in_time"].strftime("%H:%M:%S")
        if "due_date" in record and record["due_date"] is not None:
            record["due_date"] = record["due_date"].strftime("%Y-%m-%dT%H:%M:%S.%f")
        
        resp = supabase.table("challenges").insert(record).execute()
        
        if not resp.data:
            raise HTTPException(status_code=400, detail="Failed to create challenge")
        
        return resp.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating challenge: {str(e)}")

@router.get("/", response_model=list[ChallengeOut])
async def list_challenges():
    """
    List all challenges.
    
    Returns:
        list[ChallengeOut]: List of challenge objects
    """
    try:
        resp = supabase.table("challenges").select("*").execute()
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching challenges: {str(e)}")

@router.get("/{challenge_id}", response_model=ChallengeOut)
async def get_challenge(challenge_id: str):
    """
    Get a specific challenge by ID.
    
    Args:
        challenge_id (str): UUID of the challenge to retrieve
        
    Returns:
        ChallengeOut: Challenge data
        
    Raises:
        HTTPException: 404 if challenge not found
    """
    try:
        resp = supabase.table("challenges").select("*").eq("id", challenge_id).single().execute()
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=404, detail="Challenge not found")

@router.put("/{challenge_id}", response_model=ChallengeOut)
async def update_challenge(challenge_id: str, payload: ChallengeUpdate, user=Depends(get_current_user)):
    """
    Update a challenge.
    
    Args:
        challenge_id (str): UUID of the challenge to update
        payload (ChallengeUpdate): Updated challenge data
        user: Current authenticated user from token
        
    Returns:
        ChallengeOut: Updated challenge data
        
    Raises:
        HTTPException: 403 if user is not the challenge creator or content violates policy
        HTTPException: 404 if challenge not found
    """
    try:
        existing_challenge_resp = supabase.table("challenges").select("creator_id, background_photo").eq("id", challenge_id).single().execute()
        
        if not existing_challenge_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

        if existing_challenge_resp.data["creator_id"] != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this challenge")
        
        current_background_photo = existing_challenge_resp.data.get("background_photo")

        if payload.description:
            await moderate_challenge(payload.description, raise_exception=True)
            
        update_data = payload.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")

        if "background_photo" in update_data:
            new_background_photo = update_data["background_photo"] # This is List[str] or None

            if current_background_photo and isinstance(current_background_photo, list) and len(current_background_photo) == 2:
                if new_background_photo != current_background_photo:
                    try:
                        delete_file(bucket_name=current_background_photo[0], file_path=current_background_photo[1])
                    except Exception as e_del:
                        print(f"Failed to delete old background photo {current_background_photo}: {e_del}")
        
        if "check_in_time" in update_data and update_data["check_in_time"] is not None:
            update_data["check_in_time"] = update_data["check_in_time"].strftime("%H:%M:%S")
        
        supabase.table("challenges").update(update_data).eq("id", challenge_id).execute()
        
        updated = supabase.table("challenges").select("*").eq("id", challenge_id).single().execute()
        return updated.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail="Challenge not found")

@router.delete("/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_challenge(challenge_id: str, user=Depends(get_current_user)):
    """
    Delete a challenge.
    
    Args:
        challenge_id (str): UUID of the challenge to delete
        user: Current authenticated user from token
        
    Returns:
        None
        
    Raises:
        HTTPException: 403 if user is not the challenge creator
        HTTPException: 404 if challenge not found
    """
    try:
        challenge_to_delete_resp = supabase.table("challenges").select("creator_id, background_photo").eq("id", challenge_id).single().execute()
        
        if not challenge_to_delete_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
            
        if challenge_to_delete_resp.data["creator_id"] != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this challenge")
        
        background_photo_to_delete = challenge_to_delete_resp.data.get("background_photo")
        if background_photo_to_delete and isinstance(background_photo_to_delete, list) and len(background_photo_to_delete) == 2:
            try:
                delete_file(bucket_name=background_photo_to_delete[0], file_path=background_photo_to_delete[1])
            except Exception as e_del:
                print(f"Failed to delete background photo {background_photo_to_delete} for challenge {challenge_id}: {e_del}")
        
        supabase.table("challenges").delete().eq("id", challenge_id).execute()
        return None
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=404, detail="Challenge not found")

@router.post("/{challenge_id}/join", response_model=ChallengeParticipantOut, status_code=status.HTTP_201_CREATED)
async def join_challenge(challenge_id: str, user=Depends(get_current_user)):
    """
    Join a challenge.
    
    Args:
        challenge_id (str): UUID of the challenge to join
        user: Current authenticated user from token
        
    Returns:
        ChallengeParticipantOut: Challenge participant data
        
    Raises:
        HTTPException: 404 if challenge not found
        HTTPException: 400 if user is already a participant
    """
    try:
        challenge = supabase.table("challenges").select("id").eq("id", challenge_id).single().execute()
        if not challenge.data:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        existing = supabase.table("challenge_participants") \
            .select("*") \
            .eq("challenge_id", challenge_id) \
            .eq("user_id", user.id) \
            .execute()
            
        if existing.data:
            raise HTTPException(status_code=400, detail="Already joined this challenge")
        
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        participant_data = {
            "challenge_id": challenge_id,
            "user_id": user.id,
            "joined_at": now,
            "status": ParticipationStatus.ACTIVE
        }
        
        resp = supabase.table("challenge_participants").insert(participant_data).execute()
        
        if not resp.data:
            raise HTTPException(status_code=400, detail="Failed to join challenge")
        
        return resp.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Error joining challenge: {str(e)}")

@router.delete("/{challenge_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_challenge(challenge_id: str, user=Depends(get_current_user)):
    """
    Leave a challenge.
    
    Args:
        challenge_id (str): UUID of the challenge to leave
        user: Current authenticated user from token
        
    Returns:
        None
        
    Raises:
        HTTPException: 404 if challenge not found or user is not a participant
    """
    try:
        existing = supabase.table("challenge_participants") \
            .select("*") \
            .eq("challenge_id", challenge_id) \
            .eq("user_id", user.id) \
            .execute()
            
        if not existing.data:
            raise HTTPException(status_code=404, detail="Not a participant in this challenge")
        
        supabase.table("challenge_participants") \
            .delete() \
            .eq("challenge_id", challenge_id) \
            .eq("user_id", user.id) \
            .execute()
            
        return None
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Error leaving challenge: {str(e)}")

@router.get("/{challenge_id}/participants", response_model=list[ChallengeParticipantOut])
async def list_challenge_participants(challenge_id: str):
    """
    List all participants of a challenge.
    
    Args:
        challenge_id (str): UUID of the challenge
        
    Returns:
        list[ChallengeParticipantOut]: List of challenge participants
        
    Raises:
        HTTPException: 404 if challenge not found
    """
    try:
        challenge = supabase.table("challenges").select("id").eq("id", challenge_id).single().execute()
        if not challenge.data:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        resp = supabase.table("challenge_participants") \
            .select("*") \
            .eq("challenge_id", challenge_id) \
            .execute()
            
        return resp.data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Error fetching challenge participants: {str(e)}")

@router.put("/{challenge_id}/status", response_model=ChallengeParticipantOut)
async def update_participation_status(
    challenge_id: str, 
    status: ParticipationStatus,
    user=Depends(get_current_user)
):
    """
    Update participation status in a challenge.
    
    Args:
        challenge_id (str): UUID of the challenge
        status (ParticipationStatus): New participation status
        user: Current authenticated user from token
        
    Returns:
        ChallengeParticipantOut: Updated challenge participant data
        
    Raises:
        HTTPException: 404 if challenge not found or user is not a participant
    """
    try:
        existing = supabase.table("challenge_participants") \
            .select("*") \
            .eq("challenge_id", challenge_id) \
            .eq("user_id", user.id) \
            .execute()
            
        if not existing.data:
            raise HTTPException(status_code=404, detail="Not a participant in this challenge")
        
        update_data = {"status": status}
        resp = supabase.table("challenge_participants") \
            .update(update_data) \
            .eq("challenge_id", challenge_id) \
            .eq("user_id", user.id) \
            .execute()
            
        if not resp.data:
            raise HTTPException(status_code=400, detail="Failed to update status")
            
        return resp.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Error updating status: {str(e)}")

@router.get("/my/participating", response_model=list[ChallengeOut])
async def get_my_participating_challenges(user=Depends(get_current_user)):
    """
    Get all challenges the current user is participating in.
    
    Args:
        user: Current authenticated user from token
        
    Returns:
        list[ChallengeOut]: List of challenges the user is participating in
    """
    try:
        participants = supabase.table("challenge_participants") \
            .select("challenge_id") \
            .eq("user_id", user.id) \
            .execute()
            
        if not participants.data:
            return []
            
        challenge_ids = [p["challenge_id"] for p in participants.data]
        
        resp = supabase.table("challenges") \
            .select("*") \
            .in_("id", challenge_ids) \
            .execute()
            
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching challenges: {str(e)}")

@router.get("/my/created", response_model=list[ChallengeOut])
async def get_my_created_challenges(user=Depends(get_current_user)):
    """
    Get all challenges created by the current user.
    
    Args:
        user: Current authenticated user from token
        
    Returns:
        list[ChallengeOut]: List of challenges created by the user
    """
    try:
        resp = supabase.table("challenges") \
            .select("*") \
            .eq("creator_id", user.id) \
            .execute()
            
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching challenges: {str(e)}")

@router.post("/{challenge_id}/background-photo", response_model=ChallengeOut)
async def upload_challenge_background_photo(
    challenge_id: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """
    Upload or update the background photo for a challenge.
    The user must be the creator of the challenge.
    """
    challenge_resp = supabase.table("challenges") \
        .select("creator_id, background_photo") \
        .eq("id", challenge_id) \
        .single() \
        .execute()

    if not challenge_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

    if challenge_resp.data["creator_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this challenge's photo")

    old_background_photo = challenge_resp.data.get("background_photo")
    if old_background_photo and isinstance(old_background_photo, list) and len(old_background_photo) == 2:
        try:
            delete_file(bucket_name=old_background_photo[0], file_path=old_background_photo[1])
        except Exception as e:
            print(f"Failed to delete old background photo {old_background_photo}: {str(e)}")

    uploaded_filename = await upload_file("background_photo", file, f"challenge_{challenge_id}_{user.id}")
    new_photo_data = ["background_photo", uploaded_filename]

    updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    supabase.table("challenges") \
        .update({
            "background_photo": new_photo_data,
            "updated_at": updated_at
        }) \
        .eq("id", challenge_id) \
        .execute()

    return supabase.table("challenges") \
        .select("*") \
        .eq("id", challenge_id) \
        .single() \
        .execute().data

@router.get("/{challenge_id}/posts", response_model=List[PostOut])
async def list_posts_for_challenge(challenge_id: str, supabase=Depends(get_supabase)):
    """
    List all posts for a specific challenge.
    
    Args:
        challenge_id (str): UUID of the challenge
        supabase: Supabase client dependency
        
    Returns:
        list[PostOut]: List of post objects
        
    Raises:
        HTTPException: 404 if challenge not found
        HTTPException: 500 for other errors
    """
    try:
        challenge_resp = supabase.table("challenges").select("id").eq("id", challenge_id).single().execute()
        if not challenge_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

        posts_resp = supabase.table("posts").select("*").eq("challenge_id", challenge_id).execute()
        
        if posts_resp.data is None:
            return []

        return posts_resp.data
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error fetching posts for challenge {challenge_id}: {str(e)}") 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching posts for challenge: {str(e)}")

@router.get("/{challenge_id}/ranking/{metric}", response_model=list[ChallengeParticipantOut])
async def get_challenge_ranking(challenge_id: str, metric: str, supabase=Depends(get_supabase)):
    valid_metrics = ["points", "check_ins", "streak"]

    if metric not in valid_metrics:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ranking metric.")

    try:
        challenge = supabase.table("challenges").select("id").eq("id", challenge_id).single().execute()
        if not challenge.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
        
        resp = supabase.table("challenge_participants") \
            .select("*") \
            .eq("challenge_id", challenge_id) \
            .order(metric, desc=True) \
            .execute()
            
        return resp.data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching challenge ranking: {str(e)}")
    
@router.post("/media/base64", response_model=List[List[str]])
async def upload_post_media_base64(
    payload: Base64Images,
    user=Depends(get_current_user)
):
    """
    Upload base64 encoded media for a Challenge.

    Args:
        payload: JSON body containing a list of base64 image strings
        user: Current authenticated user from token

    Returns:
        List[List[str]]: List of [bucket, filename] pairs of the uploaded media

    Raises:
        HTTPException: 400 if upload fails
    """
    processed_media_items = []
    uploaded_filenames_for_cleanup = []
    try:
        for image_data in payload.base64_images:
            filename = await upload_base64_image("challenges", image_data, user.id, "image/jpg")
            processed_media_items.append(["challenges", filename])
            uploaded_filenames_for_cleanup.append(filename)

        return processed_media_items

    except Exception as e:
        for fname in uploaded_filenames_for_cleanup:
            try:
                delete_file("media_urls", fname)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=f"Failed to upload media: {str(e)}")
