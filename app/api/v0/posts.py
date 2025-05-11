from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import supabase
from app.core.deps import get_current_user
from app.schemas.posts import PostCreate, PostOut, PostUpdate

router = APIRouter(tags=["posts"])

@router.post("/", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(payload: PostCreate, user=Depends(get_current_user)):
    """
    Create a new post.
    
    Args:
        payload (PostCreate): Post data to create
        user: Current authenticated user from token
        
    Returns:
        PostOut: Created post data
        
    Raises:
        HTTPException: 400 if creation fails
    """
    record = payload.model_dump()
    record.update({"user_id": user.id, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()})
    resp = supabase.table("posts").insert(record).execute()
    if resp.error:
        raise HTTPException(status_code=400, detail=resp.error.message)
    return resp.data[0]

@router.get("/", response_model=list[PostOut])
async def list_posts():
    """
    List all posts.
    
    Returns:
        list[PostOut]: List of post objects
    """
    resp = supabase.table("posts").select("*").execute()
    return resp.data

@router.get("/{post_id}", response_model=PostOut)
async def get_post(post_id: str):
    """
    Get a specific post by ID.
    
    Args:
        post_id (str): UUID of the post to retrieve
        
    Returns:
        PostOut: Post data
        
    Raises:
        HTTPException: 404 if post not found
    """
    resp = supabase.table("posts").select("*").eq("id", post_id).single().execute()
    if resp.error:
        raise HTTPException(status_code=404, detail="Post not found")
    return resp.data

@router.put("/{post_id}", response_model=PostOut)
async def update_post(post_id: str, payload: PostUpdate, user=Depends(get_current_user)):
    """
    Update a post.
    
    Args:
        post_id (str): UUID of the post to update
        payload (PostUpdate): Updated post data
        user: Current authenticated user from token
        
    Returns:
        PostOut: Updated post data
        
    Raises:
        HTTPException: 403 if user is not the post creator
    """
    exists = supabase.table("posts").select("user_id").eq("id", post_id).single().execute()
    if exists.error or exists.data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    update_data = payload.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    supabase.table("posts").update(update_data).eq("id", post_id).execute()
    return supabase.table("posts").select("*").eq("id", post_id).single().execute().data

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: str, user=Depends(get_current_user)):
    """
    Delete a post.
    
    Args:
        post_id (str): UUID of the post to delete
        user: Current authenticated user from token
        
    Returns:
        None
        
    Raises:
        HTTPException: 403 if user is not the post creator
    """
    exists = supabase.table("posts").select("user_id").eq("id", post_id).single().execute()
    if exists.error or exists.data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    supabase.table("posts").delete().eq("id", post_id).execute()
    return None