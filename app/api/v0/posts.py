from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                     status)

from app.core.deps import get_current_user, get_supabase
from app.core.media import delete_file, upload_base64_image, upload_file
from app.core.moderation import moderate_post
from app.schemas.posts import PostCreate, PostOut, PostUpdate
from app.schemas.base64 import Base64Images

router = APIRouter(tags=["posts"])

async def update_challenge_achievements(user_id: str, challenge_id: str, supabase_client):
    """
    Update challenge achievement stats for a user.
    """
    try:
        participant_resp = supabase_client.table("challenge_participants").select("*").eq("user_id", user_id).eq("challenge_id", challenge_id).single().execute()
        
        if not participant_resp.data:
            return

        participant = participant_resp.data
        
        new_count = participant.get("count", 0) + 1
        
        # Fetch the last two posts to check for consecutive days
        posts_resp = supabase_client.table("posts") \
            .select("created_at") \
            .eq("user_id", user_id) \
            .eq("challenge_id", challenge_id) \
            .order("created_at", desc=True) \
            .limit(2) \
            .execute()
        
        new_streaks = participant.get("streaks", 0)

        if posts_resp.data and len(posts_resp.data) > 1:
            latest_post_date = datetime.fromisoformat(posts_resp.data[0]['created_at']).date()
            previous_post_date = datetime.fromisoformat(posts_resp.data[1]['created_at']).date()
            
            if (latest_post_date - previous_post_date).days == 1:
                # Consecutive days, increment streak
                new_streaks += 1
            elif (latest_post_date - previous_post_date).days > 1:
                # Not consecutive, reset streak to 1
                new_streaks = 1
            # If days are 0, it means another post on the same day, so streak does not change.
        else:
            # This is the first post for the challenge
            new_streaks = 1

        joined_date = datetime.fromisoformat(participant["joined_at"]).date()
        days_in_challenge = (datetime.now().date() - joined_date).days + 1
        new_success_rate = (new_count / days_in_challenge) if days_in_challenge > 0 else new_count

        update_data = {
            "counts": new_count,
            "streaks": new_streaks,
            "success_rate": new_success_rate
        }
        supabase_client.table("challenge_participants").update(update_data).eq("user_id", user_id).eq("challenge_id", challenge_id).execute()

    except Exception as e:
        print(f"Failed to update challenge achievements for user {user_id}, challenge {challenge_id}: {e}")

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
        HTTPException: 403 if content violates moderation policy
    """
    if payload.content:
        await moderate_post(payload.content, raise_exception=True)
        
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    
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
    
    if hasattr(payload, "challenge_id") and payload.challenge_id and payload.challenge_id != "string":
        post_data["challenge_id"] = payload.challenge_id
    
    try:
        resp = supabase.table("posts").insert(post_data).execute()
        
        if not resp.data:
            raise HTTPException(status_code=400, detail="Failed to create post")
        
        post = resp.data[0]
        
        if post.get("challenge_id"):
            await update_challenge_achievements(user.id, post["challenge_id"], supabase)
        
        if hasattr(payload, "categories") and payload.categories:
            for category in payload.categories:
                category_data = {
                    "post_id": post["id"],
                    "category": category,
                    "created_at": now
                }
                supabase.table("post_categories").insert(category_data).execute()
        
        post["endorsement_info"] = {
            "is_endorsed": False,
            "endorsement_count": 0,
            "pending_endorsement_count": 0,
            "endorser_ids": []
        }
        
        return post
    except HTTPException:
        raise
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
        HTTPException: 403 if content violates moderation policy
    """
    if content:
        await moderate_post(content, raise_exception=True)
    
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    processed_media_items = []
    
    uploaded_filenames_for_cleanup = []

    try:
        if files:
            for file_upload_obj in files:
                filename = await upload_file("media_urls", file_upload_obj, user.id)
                processed_media_items.append(["media_urls", filename])
                uploaded_filenames_for_cleanup.append(filename)
        
        post_data = {
            "user_id": user.id,
            "content": content,
            "media_urls": processed_media_items if processed_media_items else None,
            "location": location,
            "is_private": is_private,
            "created_at": now,
            "updated_at": now,
            "edited": False,
            "is_endorsed": False
        }
        
        if challenge_id and challenge_id != "string" and challenge_id.strip():
            post_data["challenge_id"] = challenge_id
        
        resp = supabase.table("posts").insert(post_data).execute()
        
        if not resp.data:
            for fname in uploaded_filenames_for_cleanup:
                try:
                    delete_file("media_urls", fname)
                except Exception as e_del:
                    pass
            raise HTTPException(status_code=400, detail="Failed to create post")
        
        post = resp.data[0]
        
        if post.get("challenge_id"):
            await update_challenge_achievements(user.id, post["challenge_id"], supabase)
        
        if categories:
            for category in categories:
                category_data = {
                    "post_id": post["id"],
                    "category": category,
                    "created_at": now
                }
                supabase.table("post_categories").insert(category_data).execute()
        
        post["endorsement_info"] = {
            "is_endorsed": False,
            "endorsement_count": 0,
            "pending_endorsement_count": 0,
            "endorser_ids": []
        }
        
        return post
    except HTTPException:
        for fname in uploaded_filenames_for_cleanup:
            try:
                delete_file("media_urls", fname)
            except Exception as e_del:
                pass
        raise
    except Exception as e:
        for fname in uploaded_filenames_for_cleanup:
            try:
                delete_file("media_urls", fname)
            except Exception as e_del:
                pass
        raise HTTPException(status_code=400, detail=f"Error creating post: {str(e)}")

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Define request body model
class Base64Images(BaseModel):
    base64_images: List[str]

@router.post("/media/base64", response_model=List[List[str]])
async def upload_post_media_base64(
    payload: Base64Images,
    user=Depends(get_current_user)
):
    """
    Upload base64 encoded media for a post.

    Args:
        payload: JSON body containing a list of base64 image strings
        user: Current authenticated user from token

    Returns:
        List[List[str]]: List of [bucket, filename] pairs of the uploaded media

    Raises:
        HTTPException: 400 if upload fails
    """
    processed_media_items = []
    uploaded_filenames_for_cleanup = []

    try:
        for image_data in payload.base64_images:
            filename = await upload_base64_image("media_urls", image_data, user.id)
            processed_media_items.append(["media_urls", filename])
            uploaded_filenames_for_cleanup.append(filename)

        return processed_media_items

    except Exception as e:
        for fname in uploaded_filenames_for_cleanup:
            try:
                delete_file("media_urls", fname)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=f"Failed to upload media: {str(e)}")


@router.post("/media", response_model=List[List[str]])
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
        List[List[str]]: List of [bucket, filename] pairs of the uploaded media
        
    Raises:
        HTTPException: 400 if upload fails
    """
    processed_media_items = []
    uploaded_filenames_for_cleanup = []
    try:
        for file_upload_obj in files:
            filename = await upload_file("media_urls", file_upload_obj, user.id)
            processed_media_items.append(["media_urls", filename])
            uploaded_filenames_for_cleanup.append(filename)
        return processed_media_items
    except Exception as e:
        for fname in uploaded_filenames_for_cleanup:
            try:
                delete_file("media_urls", fname)
            except Exception as e_del:
                pass
        raise HTTPException(status_code=400, detail=f"Failed to upload media: {str(e)}")

@router.get("/", response_model=list[PostOut])
async def list_posts(supabase=Depends(get_supabase)):
    """
    List all posts.
    
    Returns:
        list[PostOut]: List of post objects
    """
    resp = supabase.table("posts").select("*").execute()
    posts = resp.data
    
    for post in posts:
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
        HTTPException: 400 if content violates moderation policy
    """
    try:
        existing_post_resp = supabase.table("posts").select("user_id, media_urls").eq("id", post_id).single().execute()
        
        if not existing_post_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        if existing_post_resp.data["user_id"] != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this post")
        
        current_media_urls = existing_post_resp.data.get("media_urls") or []
        
        if payload.content is not None:
            await moderate_post(payload.content, raise_exception=True)
            
        update_data = payload.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        update_data["edited"] = True
        
        if "media_urls" in update_data:
            new_media_urls = update_data["media_urls"]
            
            new_media_urls_set = set(tuple(item) for item in new_media_urls) if new_media_urls else set()
            current_media_urls_set = set(tuple(item) for item in current_media_urls)

            files_to_delete = current_media_urls_set - new_media_urls_set
            
            for item_to_delete in files_to_delete:
                if isinstance(item_to_delete, tuple) and len(item_to_delete) == 2:
                    try:
                        delete_file(bucket_name=item_to_delete[0], file_path=item_to_delete[1])
                    except Exception as e_del:
                        print(f"Failed to delete old media {item_to_delete}: {e_del}")
        
        supabase.table("posts").update(update_data).eq("id", post_id).execute()
        
        updated_post = supabase.table("posts").select("*").eq("id", post_id).single().execute()
        post = updated_post.data
        
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
    except HTTPException:
        raise
    except Exception as e:
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
        post = supabase.table("posts").select("*").eq("id", post_id).single().execute()
        
        if not post.data:
            raise HTTPException(status_code=404, detail="Post not found")
            
        if post.data["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this post")
        
        if post.data.get("media_urls") and isinstance(post.data["media_urls"], list):
            for media_item in post.data["media_urls"]:
                if isinstance(media_item, list) and len(media_item) == 2:
                    try:
                        delete_file(bucket_name=media_item[0], file_path=media_item[1])
                    except Exception as e:
                        print(f"Failed to delete media file {media_item}: {str(e)}")
        
        endorsements = supabase.table("post_endorsements").select("*").eq("post_id", post_id).execute()
        if endorsements.data:
            for endorsement in endorsements.data:
                if endorsement.get("selfie_url"):
                    try:
                        delete_file("endorsements", endorsement["selfie_url"])
                    except Exception as e:
                        print(f"Failed to delete endorsement selfie {endorsement['selfie_url']}: {str(e)}")
        
        supabase.table("post_categories").delete().eq("post_id", post_id).execute()
        
        supabase.table("post_endorsements").delete().eq("post_id", post_id).execute()
            
        supabase.table("posts").delete().eq("id", post_id).execute()
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete post: {str(e)}"
        )