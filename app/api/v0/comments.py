from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import supabase
from app.core.deps import get_current_user
from app.schemas.comments import CommentCreate, CommentOut

router = APIRouter(tags=["comments"])

class CommentUpdate(BaseModel):
    """
    Schema for updating an existing comment.
    """
    content: str

@router.post("/", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(payload: CommentCreate, user=Depends(get_current_user)):
    """
    Create a new comment on a post.
    
    Args:
        payload (CommentCreate): Comment data to create
        user: Current authenticated user from token
        
    Returns:
        CommentOut: Created comment data
        
    Raises:
        HTTPException: 400 if creation fails
    """
    record = payload.model_dump()
    record.update({"user_id": user.id, "created_at": datetime.utcnow()})
    resp = supabase.table("comments").insert(record).execute()
    if resp.error:
        raise HTTPException(status_code=400, detail=resp.error.message)
    return resp.data[0]

@router.get("/", response_model=list[CommentOut])
async def list_comments(post_id: str = None):
    """
    List comments, optionally filtered by post.
    
    Args:
        post_id (str, optional): Filter comments by post ID
        
    Returns:
        list[CommentOut]: List of comment objects
    """
    query = supabase.table("comments").select("*")
    if post_id:
        query = query.eq("post_id", post_id)
    resp = query.execute()
    return resp.data

@router.get("/{comment_id}", response_model=CommentOut)
async def get_comment(comment_id: str):
    """
    Get a specific comment by ID.
    
    Args:
        comment_id (str): UUID of the comment to retrieve
        
    Returns:
        CommentOut: Comment data
        
    Raises:
        HTTPException: 404 if comment not found
    """
    resp = supabase.table("comments").select("*").eq("id", comment_id).single().execute()
    if resp.error:
        raise HTTPException(status_code=404, detail="Comment not found")
    return resp.data

@router.put("/{comment_id}", response_model=CommentOut)
async def update_comment(comment_id: str, payload: CommentUpdate, user=Depends(get_current_user)):
    """
    Update a comment.
    
    Args:
        comment_id (str): UUID of the comment to update
        payload (CommentUpdate): Updated comment content
        user: Current authenticated user from token
        
    Returns:
        CommentOut: Updated comment data
        
    Raises:
        HTTPException: 403 if user is not the comment author
    """
    exists = supabase.table("comments").select("user_id").eq("id", comment_id).single().execute()
    if exists.error or exists.data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    update_data = {"content": payload.content, "updated_at": datetime.utcnow()}
    supabase.table("comments").update(update_data).eq("id", comment_id).execute()
    return supabase.table("comments").select("*").eq("id", comment_id).single().execute().data

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: str, user=Depends(get_current_user)):
    """
    Delete a comment.
    
    Args:
        comment_id (str): UUID of the comment to delete
        user: Current authenticated user from token
        
    Returns:
        None
        
    Raises:
        HTTPException: 403 if user is not the comment author
    """
    exists = supabase.table("comments").select("user_id").eq("id", comment_id).single().execute()
    if exists.error or exists.data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    supabase.table("comments").delete().eq("id", comment_id).execute()
    return None