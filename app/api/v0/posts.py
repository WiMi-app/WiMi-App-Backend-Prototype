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
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    
    # Create the post record
    post_data = {
        "user_id": user.id,
        "content": payload.content,
        "media_urls": payload.media_urls if hasattr(payload, "media_urls") and payload.media_urls else None,
        "location": payload.location if hasattr(payload, "location") and payload.location else None,
        "is_private": payload.is_private if hasattr(payload, "is_private") else False,
        "created_at": now,
        "updated_at": now,
        "edited": False
    }
    
    # Only add challenge_id if it's a valid value and not None or empty string
    if hasattr(payload, "challenge_id") and payload.challenge_id and payload.challenge_id != "string":
        post_data["challenge_id"] = payload.challenge_id
    
    try:
        # Insert post
        resp = supabase.table("posts").insert(post_data).execute()
        
        if not resp.data:
            raise HTTPException(status_code=400, detail="Failed to create post")
        
        post = resp.data[0]
        
        # If there are categories, add them to post_categories table
        if hasattr(payload, "categories") and payload.categories:
            for category in payload.categories:
                category_data = {
                    "post_id": post["id"],
                    "category": category,
                    "created_at": now
                }
                supabase.table("post_categories").insert(category_data).execute()
        
        return post
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating post: {str(e)}")

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
    try:
        resp = supabase.table("posts").select("*").eq("id", post_id).single().execute()
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=404, detail="Post not found")

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
        HTTPException: 404 if post not found
    """
    try:
        # Check if post exists and belongs to user
        exists = supabase.table("posts").select("user_id").eq("id", post_id).single().execute()
        
        if exists.data["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this post")
            
        # Update the post
        update_data = payload.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        update_data["edited"] = True
        
        supabase.table("posts").update(update_data).eq("id", post_id).execute()
        
        # Return updated post
        updated_post = supabase.table("posts").select("*").eq("id", post_id).single().execute()
        return updated_post.data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=404, detail="Post not found")

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
        HTTPException: 404 if post not found
    """
    try:
        # Check if post exists and belongs to user
        exists = supabase.table("posts").select("user_id").eq("id", post_id).single().execute()
        
        if exists.data["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this post")
            
        # Delete the post
        supabase.table("posts").delete().eq("id", post_id).execute()
        return None
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=404, detail="Post not found")