"""
Challenges API endpoints for managing challenge resources.
Provides CRUD operations for challenges with authorization controls.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import supabase
from app.core.deps import get_current_user
from app.core.moderation import moderate_challenge
from app.schemas.challenges import (ChallengeCreate, ChallengeOut,
                                    ChallengeParticipantOut, ChallengeUpdate,
                                    ParticipationStatus)

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
        # Moderate challenge description if provided
        if payload.description:
            # This will raise an exception if moderation fails
            await moderate_challenge(payload.description, raise_exception=True)
        
        record = payload.model_dump()
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        record.update({"creator_id": user.id, "created_at": now, "updated_at": now})
        
        # Convert time to string if present
        if "check_in_time" in record and record["check_in_time"] is not None:
            record["check_in_time"] = record["check_in_time"].strftime("%H:%M:%S")
        if "due_date" in record and record["due_date"] is not None:
            record["due_date"] = record["due_date"].strftime("%Y-%m-%dT%H:%M:%S.%f")
        
        resp = supabase.table("challenges").insert(record).execute()
        
        if not resp.data:
            raise HTTPException(status_code=400, detail="Failed to create challenge")
        
        return resp.data[0]
    except HTTPException:
        # Re-raise HTTP exceptions (including moderation failures)
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
        # Check if challenge exists and belongs to user
        exists = supabase.table("challenges").select("creator_id").eq("id", challenge_id).single().execute()
        
        if exists.data["creator_id"] != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this challenge")
        
        # Moderate challenge description if provided
        if payload.description:
            # This will raise an exception if moderation fails
            await moderate_challenge(payload.description, raise_exception=True)
            
        # Update the challenge
        update_data = payload.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
            
        # Convert time to string if present
        if "check_in_time" in update_data and update_data["check_in_time"] is not None:
            update_data["check_in_time"] = update_data["check_in_time"].strftime("%H:%M:%S")
        
        supabase.table("challenges").update(update_data).eq("id", challenge_id).execute()
        
        # Return updated challenge
        updated = supabase.table("challenges").select("*").eq("id", challenge_id).single().execute()
        return updated.data
    except HTTPException:
        # Re-raise HTTP exceptions (including moderation failures)
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
        # Check if challenge exists and belongs to user
        exists = supabase.table("challenges").select("creator_id").eq("id", challenge_id).single().execute()
            
        if exists.data["creator_id"] != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this challenge")
            
        # Delete the challenge
        supabase.storage.from_("challenges").delete(f"{challenge_id}/background_photo")
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
        # Check if challenge exists
        challenge = supabase.table("challenges").select("id").eq("id", challenge_id).single().execute()
        if not challenge.data:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        # Check if user is already a participant
        existing = supabase.table("challenge_participants") \
            .select("*") \
            .eq("challenge_id", challenge_id) \
            .eq("user_id", user.id) \
            .execute()
            
        if existing.data:
            raise HTTPException(status_code=400, detail="Already joined this challenge")
        
        # Join the challenge
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
        # Check if user is a participant
        existing = supabase.table("challenge_participants") \
            .select("*") \
            .eq("challenge_id", challenge_id) \
            .eq("user_id", user.id) \
            .execute()
            
        if not existing.data:
            raise HTTPException(status_code=404, detail="Not a participant in this challenge")
        
        # Leave the challenge
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
        # Check if challenge exists
        challenge = supabase.table("challenges").select("id").eq("id", challenge_id).single().execute()
        if not challenge.data:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        # Get participants
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
        # Check if user is a participant
        existing = supabase.table("challenge_participants") \
            .select("*") \
            .eq("challenge_id", challenge_id) \
            .eq("user_id", user.id) \
            .execute()
            
        if not existing.data:
            raise HTTPException(status_code=404, detail="Not a participant in this challenge")
        
        # Update status
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
        # Get all challenge IDs the user is participating in
        participants = supabase.table("challenge_participants") \
            .select("challenge_id") \
            .eq("user_id", user.id) \
            .execute()
            
        if not participants.data:
            return []
            
        # Get challenge IDs
        challenge_ids = [p["challenge_id"] for p in participants.data]
        
        # Get challenge details
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