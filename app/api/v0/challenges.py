from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from app.core.config import supabase
from app.core.deps import get_current_user
from app.schemas.challenges import ChallengeCreate, ChallengeUpdate, ChallengeOut

router = APIRouter(tags=["challenges"])

@router.post("/", response_model=ChallengeOut, status_code=status.HTTP_201_CREATED)
async def create_challenge(payload: ChallengeCreate, user=Depends(get_current_user)):
    record = payload.dict()
    record.update({"creator_id": user.id, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()})
    resp = supabase.table("challenges").insert(record).execute()
    if resp.error:
        raise HTTPException(status_code=400, detail=resp.error.message)
    return resp.data[0]

@router.get("/", response_model=list[ChallengeOut])
async def list_challenges():
    resp = supabase.table("challenges").select("*").execute()
    return resp.data

@router.get("/{challenge_id}", response_model=ChallengeOut)
async def get_challenge(challenge_id: str):
    resp = supabase.table("challenges").select("*").eq("id", challenge_id).single().execute()
    if resp.error:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return resp.data

@router.put("/{challenge_id}", response_model=ChallengeOut)
async def update_challenge(challenge_id: str, payload: ChallengeUpdate, user=Depends(get_current_user)):
    exists = supabase.table("challenges").select("creator_id").eq("id", challenge_id).single().execute()
    if exists.error or exists.data["creator_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    update_data = payload.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    supabase.table("challenges").update(update_data).eq("id", challenge_id).execute()
    return supabase.table("challenges").select("*").eq("id", challenge_id).single().execute().data

@router.delete("/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_challenge(challenge_id: str, user=Depends(get_current_user)):
    exists = supabase.table("challenges").select("creator_id").eq("id", challenge_id).single().execute()
    if exists.error or exists.data["creator_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    supabase.table("challenges").delete().eq("id", challenge_id).execute()
    return None