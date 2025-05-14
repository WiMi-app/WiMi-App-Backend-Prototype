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
    try:
        record = payload.model_dump()
        # Convert datetime to string to make it JSON serializable
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")
        record.update({"user_id": user.id, "created_at": now})
        
        resp = supabase.table("comments").insert(record).execute()
        
        if not resp.data:
            raise HTTPException(status_code=400, detail="Failed to create comment")
            
        return resp.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating comment: {str(e)}")

@router.get("/", response_model=list[CommentOut])
async def list_comments(post_id: str = None):
    """
    List comments, optionally filtered by post.
    
    Args:
        post_id (str, optional): Filter comments by post ID
        
    Returns:
        list[CommentOut]: List of comment objects
    """
    try:
        query = supabase.table("comments").select("*")
        if post_id:
            query = query.eq("post_id", post_id)
        resp = query.execute()
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching comments: {str(e)}")

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
    try:
        resp = supabase.table("comments").select("*").eq("id", comment_id).single().execute()
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=404, detail="Comment not found")

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
        HTTPException: 404 if comment not found
    """
    try:
        # Check if comment exists and belongs to user
        exists = supabase.table("comments").select("user_id").eq("id", comment_id).single().execute()
        
        if exists.data["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this comment")
            
        # Update only the content field
        update_data = {"content": payload.content}
        
        # Update the comment
        supabase.table("comments").update(update_data).eq("id", comment_id).execute()
        
        # Return updated comment
        updated_comment = supabase.table("comments").select("*").eq("id", comment_id).single().execute()
        return updated_comment.data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=404, detail="Comment not found")

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
        HTTPException: 403 if user is neither the comment author nor the post owner
        HTTPException: 404 if comment not found
    """
    try:
        # Get the comment details including post_id and user_id
        comment = supabase.table("comments").select("user_id,post_id").eq("id", comment_id).single().execute()
        
        if not comment.data:
            raise HTTPException(status_code=404, detail="Comment not found")
            
        comment_user_id = comment.data["user_id"]
        post_id = comment.data["post_id"]
        
        # Check if user is the comment author (direct permission)
        is_comment_author = comment_user_id == user.id
        
        # Check if user is the post owner (has permission to moderate their own post)
        post_owner = False
        if not is_comment_author:
            post = supabase.table("posts").select("user_id").eq("id", post_id).single().execute()
            post_owner = post.data and post.data["user_id"] == user.id
        
        # Allow delete if user is either comment author or post owner
        if not (is_comment_author or post_owner):
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to delete this comment. You must be either the comment author or the post owner."
            )
            
        # Delete the comment
        supabase.table("comments").delete().eq("id", comment_id).execute()
        return None
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=404, detail=f"Error deleting comment: {str(e)}")