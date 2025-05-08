from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from app.core.config import supabase
from app.core.deps import get_current_user
from app.schemas.posts import PostCreate, PostUpdate, PostOut

router = APIRouter(tags=["posts"])

@router.post("/", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(payload: PostCreate, user=Depends(get_current_user)):
    record = payload.dict()
    record.update({"user_id": user.id, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()})
    resp = supabase.table("posts").insert(record).execute()
    if resp.error:
        raise HTTPException(status_code=400, detail=resp.error.message)
    return resp.data[0]

@router.get("/", response_model=list[PostOut])
async def list_posts():
    resp = supabase.table("posts").select("*").execute()
    return resp.data

@router.get("/{post_id}", response_model=PostOut)
async def get_post(post_id: str):
    resp = supabase.table("posts").select("*").eq("id", post_id).single().execute()
    if resp.error:
        raise HTTPException(status_code=404, detail="Post not found")
    return resp.data

@router.put("/{post_id}", response_model=PostOut)
async def update_post(post_id: str, payload: PostUpdate, user=Depends(get_current_user)):
    exists = supabase.table("posts").select("user_id").eq("id", post_id).single().execute()
    if exists.error or exists.data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    update_data = payload.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    supabase.table("posts").update(update_data).eq("id", post_id).execute()
    return supabase.table("posts").select("*").eq("id", post_id).single().execute().data

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: str, user=Depends(get_current_user)):
    exists = supabase.table("posts").select("user_id").eq("id", post_id).single().execute()
    if exists.error or exists.data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    supabase.table("posts").delete().eq("id", post_id).execute()
    return None