import logging
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.core.deps import get_current_user, get_supabase
from app.schemas.likes import LikeCreate, LikeOut
from app.schemas.users import UserOut

router = APIRouter(tags=["likes"])

@router.post(
    "/",
    response_model=LikeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Like a post (idempotent)",
)
def like_post(
    payload: LikeCreate,
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """
    Create a like for a post by the current user.
    
    Args:
        payload (LikeCreate): Contains post_id to like
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        idempotency_key: Optional key for idempotent requests
        
    Returns:
        LikeOut: The created like record
        
    Raises:
        HTTPException: 400 if database operation fails
    """
    data = {"user_id": current_user.id, "post_id": payload.post_id}
    try:
        # First check if like already exists
        existing = supabase.table("likes").select("*") \
            .eq("user_id", current_user.id) \
            .eq("post_id", payload.post_id) \
            .execute()
            
        # If like exists, return it
        if existing.data and len(existing.data) > 0:
            return existing.data[0]
            
        # Otherwise create new like
        res = supabase.table("likes").insert(data).execute()
        if not res.data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to create like")
        return res.data[0]
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error: {str(e)}")

@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a like",
)
def unlike_post(
    post_id: str,
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """
    Remove a like by its ID.
    
    Args:
        post_id (str): UUID of the post to unlike
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        idempotency_key: Optional idempotency key for duplicate request prevention
        
    Returns:
        Response: 204 No Content on success
        
    Raises:
        HTTPException: 404 if like not found
        HTTPException: 403 if user is not authorized to remove the like
        HTTPException: 400 if database operation fails
    """
    try:
        # Check if like exists and belongs to current user
        rec = supabase.table("likes").select("*").eq("user_id", current_user.id).eq("post_id", post_id).execute()
        
        if not rec.data or len(rec.data) == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Like not found")
        
        # No need to check user_id again since we already filtered by current_user.id
        
        # Delete the like
        supabase.table("likes").delete().eq("user_id", current_user.id).eq("post_id", post_id).execute()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error: {str(e)}")
    
@router.get("/me/{post_id}")
def get_MyLike(
    post_id: str,
    current_user=Depends(get_current_user),
    supabase=Depends(get_supabase),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key")
):
    """
    Get if I liked a specific post.

    Args: 
        post_id (str): UUID of the post to check
        current_user: Current authenticated user from token
        supabase: Supabase client instance
        idempotency_key: Optional idempotency key (unused in this context)
    
    Returns:
        dict: {"liked": bool, "like_id": str | None} - Whether user liked the post and the like ID if it exists

    Raises:
        HTTPException: 400 if database operation fails
        HTTPException: 401 if user is not authenticated
    """
    try:
        # Check if current user has liked this post
        rec = supabase.table("likes").select("*").eq("user_id", current_user.id).eq("post_id", post_id).execute()
        
        if rec.data and len(rec.data) > 0:
            return {
                "liked": True,
                "like_id": rec.data[0].get("id")  # or whatever your like ID field is called
            }
        else:
            return {
                "liked": False,
                "like_id": None
            }
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error checking like status: {str(e)}")

@router.get(
    "/by-post/{post_id}/users",
    response_model=List[UserOut],
    summary="Get users who liked a specific post",
)
def get_users_who_liked_post(
    post_id: str,
    supabase=Depends(get_supabase),
):
    """
    Get a list of users who liked a specific post.
    
    Args:
        post_id (str): UUID of the post
        supabase: Supabase client instance
        
    Returns:
        List[UserOut]: List of users who liked the post
        
    Raises:
        HTTPException: 400 if database operation fails
        HTTPException: 404 if post not found (implicitly, if no likes exist)
    """
    try:
        # Fetch user_ids of users who liked the post
        likes_res = supabase.table("likes").select("user_id").eq("post_id", post_id).execute()
        if not likes_res.data:
            return [] # Return empty list if no likes for the post

        user_ids = [like['user_id'] for like in likes_res.data]
        if not user_ids:
            return []

        # Fetch user details for those user_ids
        users_res = supabase.table("users").select("id, username, full_name, avatar_url, email, bio, updated_at").in_("id", user_ids).execute()
        
        if not users_res.data:
            return []
            
        return users_res.data
    except Exception as e:

        logging.error(f"Error fetching users who liked post {post_id}: {str(e)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error fetching users who liked post: {str(e)}")
