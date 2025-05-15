from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import supabase
from app.core.deps import get_current_user
from app.schemas.posts import PostOut, SavedPostCreate

router = APIRouter(tags=["saved_posts"])

@router.post("/", status_code=status.HTTP_201_CREATED)
async def save_post(payload: SavedPostCreate, user=Depends(get_current_user)):
    """
    Save a post for the current user.
    
    Args:
        payload (SavedPostCreate): Post ID to save
        user: Current authenticated user from token
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: 400 if post cannot be saved
        HTTPException: 404 if post not found
    """
    # Check if post exists
    try:
        post_exists = supabase.table("posts").select("id").eq("id", payload.post_id).single().execute()
        if not post_exists.data:
            raise HTTPException(status_code=404, detail="Post not found")
    except Exception as e:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if already saved
    already_saved = supabase.table("user_saved_posts")\
        .select("*")\
        .eq("user_id", user.id)\
        .eq("post_id", payload.post_id)\
        .execute()
        
    if already_saved.data:
        return {"message": "Post already saved"}
    
    # Save the post
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    saved_post_data = {
        "user_id": user.id,
        "post_id": payload.post_id,
        "created_at": now
    }
    
    try:
        supabase.table("user_saved_posts").insert(saved_post_data).execute()
        return {"message": "Post saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error saving post: {str(e)}")

@router.get("/{post_id}/check", response_model=dict)
async def check_saved_post(post_id: str, user=Depends(get_current_user)):
    """
    Check if a post is saved by the current user.
    
    Args:
        post_id (str): UUID of the post to check
        user: Current authenticated user from token
        
    Returns:
        dict: Boolean "is_saved" indicating if post is saved
    """
    try:
        saved_post = supabase.table("user_saved_posts")\
            .select("*")\
            .eq("user_id", user.id)\
            .eq("post_id", post_id)\
            .execute()
            
        return {"is_saved": len(saved_post.data) > 0}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error checking saved status: {str(e)}")

@router.delete("/{post_id}", status_code=status.HTTP_200_OK)
async def unsave_post(post_id: str, user=Depends(get_current_user)):
    """
    Unsave (remove) a saved post for the current user.
    
    Args:
        post_id (str): UUID of the post to unsave
        user: Current authenticated user from token
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: 404 if saved post not found
    """
    try:
        # Check if post is saved by user
        saved_post = supabase.table("user_saved_posts")\
            .select("*")\
            .eq("user_id", user.id)\
            .eq("post_id", post_id)\
            .execute()
            
        if not saved_post.data:
            raise HTTPException(status_code=404, detail="Saved post not found")
            
        # Delete the saved post
        supabase.table("user_saved_posts")\
            .delete()\
            .eq("user_id", user.id)\
            .eq("post_id", post_id)\
            .execute()
            
        return {"message": "Post unsaved successfully"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Error unsaving post: {str(e)}")

@router.get("/", response_model=list[PostOut])
async def get_saved_posts(user=Depends(get_current_user)):
    """
    Get all posts saved by the current user.
    
    Args:
        user: Current authenticated user from token
        
    Returns:
        list[PostOut]: List of saved post objects
    """
    try:
        # Get all saved post IDs for the user
        saved_posts = supabase.table("user_saved_posts")\
            .select("post_id")\
            .eq("user_id", user.id)\
            .execute()
            
        if not saved_posts.data:
            return []
            
        # Extract post IDs
        post_ids = [saved_post["post_id"] for saved_post in saved_posts.data]
        
        # Get the full post data for each saved post
        posts = supabase.table("posts")\
            .select("*")\
            .in_("id", post_ids)\
            .execute()
            
        return posts.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error retrieving saved posts: {str(e)}") 