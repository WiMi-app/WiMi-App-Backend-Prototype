"""
Challenges API endpoints for managing challenge resources.
Provides CRUD operations for challenges with authorization controls.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import supabase
from app.core.deps import get_current_user
from app.schemas.challenges import (ChallengeCreate, ChallengeOut,
                                    ChallengeUpdate)

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
        HTTPException: 400 if creation fails
    """
    record = payload.model_dump()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    record.update({"creator_id": user.id, "created_at": now, "updated_at": now})
    resp = supabase.table("challenges").insert(record).execute()
    if resp.error:
        raise HTTPException(status_code=400, detail=resp.error.message)
    return resp.data[0]

@router.get("/", response_model=list[ChallengeOut])
async def list_challenges():
    """
    List all challenges.
    
    Returns:
        list[ChallengeOut]: List of challenge objects
    """
    resp = supabase.table("challenges").select("*").execute()
    return resp.data

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
    resp = supabase.table("challenges").select("*").eq("id", challenge_id).single().execute()
    if resp.error:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return resp.data

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
        HTTPException: 403 if user is not the challenge creator
    """
    exists = supabase.table("challenges").select("creator_id").eq("id", challenge_id).single().execute()
    if exists.error or exists.data["creator_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    update_data = payload.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    supabase.table("challenges").update(update_data).eq("id", challenge_id).execute()
    return supabase.table("challenges").select("*").eq("id", challenge_id).single().execute().data

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
    """
    exists = supabase.table("challenges").select("creator_id").eq("id", challenge_id).single().execute()
    if exists.error or exists.data["creator_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    supabase.table("challenges").delete().eq("id", challenge_id).execute()
    return None