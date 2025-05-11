from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from app.core.config import supabase
from app.core.deps import get_current_user
from app.schemas.users import UserUpdate
from app.schemas.users import UserOut

router = APIRouter(tags=["users"])

@router.get("/me", response_model=UserOut)
async def read_current_user(user=Depends(get_current_user)):
    return UserOut(**user.__dict__)

@router.get("/{user_id}", response_model=UserOut)
async def read_user(user_id: str):
    resp = supabase.table("users")\
        .select("id,email,full_name,avatar_url")\
            .eq("id", user_id).single().execute()
    if resp.error:
        raise HTTPException(status_code=404, detail="User not found")
    return resp.data

@router.put("/me", response_model=UserOut)
async def update_user(payload: UserUpdate, user=Depends(get_current_user)):
    data = payload.model_dump(exclude_unset=True)
    data["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    supabase.table("users").update(data).eq("id", user.id).execute()
    return supabase.table("users")\
        .select("id,username,email,full_name,avatar_url")\
        .eq("id", user.id)\
        .single().execute().data