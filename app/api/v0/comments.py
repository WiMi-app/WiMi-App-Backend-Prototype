from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from pydantic import BaseModel

from app.core.config import supabase
from app.core.deps import get_current_user
from app.schemas.comments import CommentCreate, CommentOut

router = APIRouter(tags=["comments"])

class CommentUpdate(BaseModel):
    content: str

@router.post("/", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(payload: CommentCreate, user=Depends(get_current_user)):
    record = payload.dict()
    record.update({"user_id": user.id, "created_at": datetime.utcnow()})
    resp = supabase.table("comments").insert(record).execute()
    if resp.error:
        raise HTTPException(status_code=400, detail=resp.error.message)
    return resp.data[0]

@router.get("/", response_model=list[CommentOut])
async def list_comments(post_id: str = None):
    query = supabase.table("comments").select("*")
    if post_id:
        query = query.eq("post_id", post_id)
    resp = query.execute()
    return resp.data

@router.get("/{comment_id}", response_model=CommentOut)
async def get_comment(comment_id: str):
    resp = supabase.table("comments").select("*").eq("id", comment_id).single().execute()
    if resp.error:
        raise HTTPException(status_code=404, detail="Comment not found")
    return resp.data

@router.put("/{comment_id}", response_model=CommentOut)
async def update_comment(comment_id: str, payload: CommentUpdate, user=Depends(get_current_user)):
    exists = supabase.table("comments").select("user_id").eq("id", comment_id).single().execute()
    if exists.error or exists.data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    update_data = {"content": payload.content, "updated_at": datetime.utcnow()}
    supabase.table("comments").update(update_data).eq("id", comment_id).execute()
    return supabase.table("comments").select("*").eq("id", comment_id).single().execute().data

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: str, user=Depends(get_current_user)):
    exists = supabase.table("comments").select("user_id").eq("id", comment_id).single().execute()
    if exists.error or exists.data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    supabase.table("comments").delete().eq("id", comment_id).execute()
    return None