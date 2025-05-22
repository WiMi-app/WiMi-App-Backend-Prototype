from datetime import datetime
from typing import List, Optional

from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                     status)

from app.core.config import supabase
from app.core.deps import get_current_user, get_supabase
from app.core.media import delete_file, upload_base64_image, upload_file
from app.schemas.posts import (PostCreate, PostEndorsementInfo, PostOut,
                               PostUpdate)

router = APIRouter(tags=["posts"])

@router.post("/", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(payload: PostCreate, user=Depends(get_current_user), supabase=Depends(get_supabase)):
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
        "edited": False,
        "is_endorsed": False
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
        
        # Add empty endorsement info
        post["endorsement_info"] = {
            "is_endorsed": False,
            "endorsement_count": 0,
            "pending_endorsement_count": 0,
            "endorser_ids": []
        }
        
        return post
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating post: {str(e)}")

@router.post("/with-media", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post_with_media(
    content: str = Form(...),
    location: Optional[str] = Form(None),
    is_private: bool = Form(False),
    challenge_id: Optional[str] = Form(None),
    categories: Optional[List[str]] = Form(None),
    files: List[UploadFile] = File(None),
    user=Depends(get_current_user),
    supabase=Depends(get_supabase)
):
    """
    Create a new post with media uploads.
    
    Args:
        content: Text content of the post
        location: Optional location string
        is_private: Whether the post is private
        challenge_id: Optional challenge ID
        categories: Optional list of categories
        files: List of media files to upload
        user: Current authenticated user from token
        
    Returns:
        PostOut: Created post data with media URLs
        
    Raises:
        HTTPException: 400 if creation fails
    """
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    media_urls = []
    
    try:
        # Upload all media files
        if files:
            for file in files:
                media_url = await upload_file("post_media", file, user.id)
                media_urls.append(media_url)
        
        # Create the post record
        post_data = {
            "user_id": user.id,
            "content": content,
            "media_urls": media_urls if media_urls else None,
            "location": location,
            "is_private": is_private,
            "created_at": now,
            "updated_at": now,
            "edited": False,
            "is_endorsed": False
        }
        
        # Only add challenge_id if it's valid
        if challenge_id and challenge_id != "string" and challenge_id.strip():
            post_data["challenge_id"] = challenge_id
        
        # Insert post
        resp = supabase.table("posts").insert(post_data).execute()
        
        if not resp.data:
            # Clean up any uploaded files if post creation fails
            for url in media_urls:
                try:
                    delete_file("post_media", url)
                except:
                    pass
            raise HTTPException(status_code=400, detail="Failed to create post")
        
        post = resp.data[0]
        
        # If there are categories, add them
        if categories:
            for category in categories:
                category_data = {
                    "post_id": post["id"],
                    "category": category,
                    "created_at": now
                }
                supabase.table("post_categories").insert(category_data).execute()
        
        # Add empty endorsement info
        post["endorsement_info"] = {
            "is_endorsed": False,
            "endorsement_count": 0,
            "pending_endorsement_count": 0,
            "endorser_ids": []
        }
        
        return post
    except Exception as e:
        # Clean up any uploaded files if post creation fails
        for url in media_urls:
            try:
                delete_file("post_media", url)
            except:
                pass
        raise HTTPException(status_code=400, detail=f"Error creating post: {str(e)}")

@router.post("/media/base64", response_model=List[str])
async def upload_post_media_base64(
    base64_images: List[str] = Form(...),
    user=Depends(get_current_user)
):
    """
    Upload base64 encoded media for a post.
    
    Args:
        base64_images: List of base64 encoded image data
        user: Current authenticated user from token
        
    Returns:
        List[str]: List of URLs of the uploaded media
        
    Raises:
        HTTPException: 400 if upload fails
    """
    media_urls = []
    try:
        for image_data in base64_images:
            url = await upload_base64_image("post_media", image_data, user.id)
            media_urls.append(url)
        return media_urls
    except Exception as e:
        # Clean up any files that were uploaded before the error
        for url in media_urls:
            try:
                delete_file("post_media", url)
            except:
                pass
        raise HTTPException(status_code=400, detail=f"Failed to upload media: {str(e)}")

@router.post("/media", response_model=List[str])
async def upload_post_media(
    files: List[UploadFile] = File(...),
    user=Depends(get_current_user)
):
    """
    Upload media files for a post.
    
    Args:
        files: List of files to upload
        user: Current authenticated user from token
        
    Returns:
        List[str]: List of URLs of the uploaded media
        
    Raises:
        HTTPException: 400 if upload fails
    """
    media_urls = []
    try:
        for file in files:
            url = await upload_file("post_media", file, user.id)
            media_urls.append(url)
        return media_urls
    except Exception as e:
        # Clean up any files that were uploaded before the error
        for url in media_urls:
            try:
                delete_file("post_media", url)
            except:
                pass
        raise HTTPException(status_code=400, detail=f"Failed to upload media: {str(e)}")

@router.get("/", response_model=list[PostOut])
async def list_posts(supabase=Depends(get_supabase)):
    """
    List all posts.
    
    Returns:
        list[PostOut]: List of post objects
    """
    # Get all posts
    resp = supabase.table("posts").select("*").execute()
    posts = resp.data
    
    # Add endorsement info to each post
    for post in posts:
        # Get endorsements for this post
        endorsements = supabase.table("post_endorsements")\
            .select("*")\
            .eq("post_id", post["id"])\
            .execute()
            
        endorsed_count = sum(1 for e in endorsements.data if e["status"] == "endorsed")
        pending_count = sum(1 for e in endorsements.data if e["status"] == "pending")
        endorser_ids = [e["endorser_id"] for e in endorsements.data if e["status"] == "endorsed"]
        
        post["endorsement_info"] = {
            "is_endorsed": post.get("is_endorsed", False),
            "endorsement_count": endorsed_count,
            "pending_endorsement_count": pending_count,
            "endorser_ids": endorser_ids
        }
    
    return posts

@router.get("/{post_id}", response_model=PostOut)
async def get_post(post_id: str, supabase=Depends(get_supabase)):
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
        post = resp.data
        
        # Get endorsements for this post
        endorsements = supabase.table("post_endorsements")\
            .select("*")\
            .eq("post_id", post_id)\
            .execute()
            
        endorsed_count = sum(1 for e in endorsements.data if e["status"] == "endorsed")
        pending_count = sum(1 for e in endorsements.data if e["status"] == "pending")
        endorser_ids = [e["endorser_id"] for e in endorsements.data if e["status"] == "endorsed"]
        
        post["endorsement_info"] = {
            "is_endorsed": post.get("is_endorsed", False),
            "endorsement_count": endorsed_count,
            "pending_endorsement_count": pending_count,
            "endorser_ids": endorser_ids
        }
        
        return post
    except Exception as e:
        raise HTTPException(status_code=404, detail="Post not found")

@router.put("/{post_id}", response_model=PostOut)
async def update_post(post_id: str, payload: PostUpdate, user=Depends(get_current_user), supabase=Depends(get_supabase)):
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
        
        # Return updated post with endorsement info
        updated_post = supabase.table("posts").select("*").eq("id", post_id).single().execute()
        post = updated_post.data
        
        # Get endorsements for this post
        endorsements = supabase.table("post_endorsements")\
            .select("*")\
            .eq("post_id", post_id)\
            .execute()
            
        endorsed_count = sum(1 for e in endorsements.data if e["status"] == "endorsed")
        pending_count = sum(1 for e in endorsements.data if e["status"] == "pending")
        endorser_ids = [e["endorser_id"] for e in endorsements.data if e["status"] == "endorsed"]
        
        post["endorsement_info"] = {
            "is_endorsed": post.get("is_endorsed", False),
            "endorsement_count": endorsed_count,
            "pending_endorsement_count": pending_count,
            "endorser_ids": endorser_ids
        }
        
        return post
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=404, detail="Post not found")

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: str, user=Depends(get_current_user), supabase=Depends(get_supabase)):
    """
    Delete a post and its associated media files.
    
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
        post = supabase.table("posts").select("*").eq("id", post_id).single().execute()
        
        if not post.data:
            raise HTTPException(status_code=404, detail="Post not found")
            
        if post.data["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this post")
        
        # Delete associated media files if any
        if post.data.get("media_urls") and isinstance(post.data["media_urls"], list):
            for media_url in post.data["media_urls"]:
                try:
                    delete_file("post_media", media_url)
                except Exception as e:
                    # Log the error but continue with deletion
                    print(f"Failed to delete media file {media_url}: {str(e)}")
        
        # Delete associated endorsement selfies if any
        endorsements = supabase.table("post_endorsements").select("*").eq("post_id", post_id).execute()
        if endorsements.data:
            for endorsement in endorsements.data:
                if endorsement.get("selfie_url"):
                    try:
                        delete_file("endorsements", endorsement["selfie_url"])
                    except Exception as e:
                        # Log the error but continue with deletion
                        print(f"Failed to delete endorsement selfie {endorsement['selfie_url']}: {str(e)}")
        
        # Delete related data from post_categories
        supabase.table("post_categories").delete().eq("post_id", post_id).execute()
        
        # Delete related data from post_endorsements
        supabase.table("post_endorsements").delete().eq("post_id", post_id).execute()
            
        # Delete the post
        supabase.table("posts").delete().eq("id", post_id).execute()
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete post: {str(e)}"
        )