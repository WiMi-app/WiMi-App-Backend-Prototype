import json
from datetime import datetime, timedelta
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.core.deps import get_current_active_user
from app.db.database import get_supabase
from app.schemas.posts import Post, PostCreate, PostUpdate, PostWithDetails, UserSavedPostCreate
from app.schemas.users import User
from app.core.moderation import moderate_content

router = APIRouter()


@router.post("/", response_model=Post)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Create a new post.
    """
    # First, moderate the content
    moderation_result = await moderate_content(
        text_content=post_data.content,
        image_urls=post_data.media_urls if post_data.media_urls else None
    )
    
    # Check if content was flagged
    if moderation_result.flagged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content violates community guidelines and cannot be posted",
        )
        
    now = datetime.now().isoformat()
        
    # Prepare the post data for insertion
    post_dict = post_data.model_dump()
    post_dict.update({
        "user_id": str(current_user.id),
        "created_at": now,
        "updated_at": now,
    })
    
    # Convert media_urls to JSON string if it's a list
    # This is the simplest way to handle array data for tests
    if "media_urls" in post_dict and isinstance(post_dict["media_urls"], list):
        # Use PostgreSQL array literal format instead of just JSON encoding
        if len(post_dict["media_urls"]) > 0:
            # Convert to PostgreSQL array format
            post_dict["media_urls"] = "{" + ",".join(f'"{url}"' for url in post_dict["media_urls"]) + "}"
        else:
            post_dict["media_urls"] = "{}"
    
    result = db.table("posts").insert(post_dict).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post",
        )
    
    # Convert media_urls back to list for response
    post_data = result.data[0]
    if "media_urls" in post_data and isinstance(post_data["media_urls"], str):
        try:
            # Check if it's PostgreSQL array format (starts with '{' and ends with '}')
            if post_data["media_urls"].startswith('{') and post_data["media_urls"].endswith('}'):
                # Parse PostgreSQL array format
                if post_data["media_urls"] == "{}":
                    post_data["media_urls"] = []
                else:
                    # Remove the curly braces and split by commas, then remove quotes
                    urls = post_data["media_urls"][1:-1].split(',')
                    post_data["media_urls"] = [url.strip('"') for url in urls]
            else:
                # Fallback to JSON parsing for backward compatibility
                post_data["media_urls"] = json.loads(post_data["media_urls"])
        except:
            # Fallback if not valid JSON or array format
            post_data["media_urls"] = []
    
    # Extract hashtags from content
    content = post_data["content"]
    hashtags = []
    
    for word in content.split():
        if word.startswith("#") and len(word) > 1:
            tag = word[1:]  # Remove the # symbol
            hashtags.append(tag)
    
    # Save hashtags and create post-hashtag associations
    for tag in hashtags:
        # Check if hashtag exists
        existing_tag = db.table("hashtags").select("*").eq("name", tag).execute()
        
        if existing_tag.data and len(existing_tag.data) > 0:
            hashtag_id = existing_tag.data[0]["id"]
        else:
            # Create new hashtag
            new_tag = db.table("hashtags").insert({"name": tag, "created_at": now}).execute()
            hashtag_id = new_tag.data[0]["id"]
        
        # Create post-hashtag association
        db.table("post_hashtags").insert({
            "post_id": post_data["id"],
            "hashtag_id": hashtag_id,
            "created_at": now,
        }).execute()
    
    return Post(**post_data)


@router.get("/", response_model=List[PostWithDetails])
def get_posts(
    skip: int = 0,
    limit: int = 10,
    user_id: Optional[UUID] = None,
    hashtag: Optional[str] = None,
    challenge_id: Optional[UUID] = None,
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Get all posts with optional filtering.
    """
    query = db.table("posts") \
        .select("*") \
        .order("created_at", desc=True)
    
    if user_id:
        query = query.eq("user_id", str(user_id))
    
    if hashtag:
        # This is a simplistic approach - in a real app, you'd use a join
        hashtag_data = db.table("hashtags").select("id").eq("name", hashtag).execute()
        
        if hashtag_data.data and len(hashtag_data.data) > 0:
            hashtag_id = hashtag_data.data[0]["id"]
            post_hashtags = db.table("post_hashtags").select("post_id").eq("hashtag_id", hashtag_id).execute()
            
            if post_hashtags.data and len(post_hashtags.data) > 0:
                post_ids = [ph["post_id"] for ph in post_hashtags.data]
                query = query.in_("id", post_ids)
            else:
                return []
        else:
            return []
    
    if challenge_id:
        # Filter posts by challenge
        challenge_posts = db.table("challenge_posts").select("post_id").eq("challenge_id", str(challenge_id)).execute()
        
        if not challenge_posts.data or len(challenge_posts.data) == 0:
            return []
        
        post_ids = [cp["post_id"] for cp in challenge_posts.data]
        query = query.in_("id", post_ids)
    
    posts = query.range(skip, skip + limit - 1).execute()
    
    if not posts.data:
        return []
    
    result = []
    
    for post in posts.data:
        # Convert media_urls from string to list
        if "media_urls" in post and isinstance(post["media_urls"], str):
            try:
                # Check if it's PostgreSQL array format (starts with '{' and ends with '}')
                if post["media_urls"].startswith('{') and post["media_urls"].endswith('}'):
                    # Parse PostgreSQL array format
                    if post["media_urls"] == "{}":
                        post["media_urls"] = []
                    else:
                        # Remove the curly braces and split by commas, then remove quotes
                        urls = post["media_urls"][1:-1].split(',')
                        post["media_urls"] = [url.strip('"') for url in urls]
                else:
                    # Fallback to JSON parsing for backward compatibility
                    post["media_urls"] = json.loads(post["media_urls"])
            except:
                post["media_urls"] = []
        
        # Get user data
        user_data = db.table("users").select("*").eq("id", post["user_id"]).execute()
        
        if user_data.data and len(user_data.data) > 0:
            user = user_data.data[0]
        else:
            user = None
        
        # Get comments count
        comments_count = db.table("comments").select("id", count="exact").eq("post_id", post["id"]).execute()
        
        # Get likes count
        likes_count = db.table("likes").select("id", count="exact").eq("post_id", post["id"]).execute()
        
        # Get hashtags
        post_hashtags = db.table("post_hashtags") \
            .select("hashtag_id") \
            .eq("post_id", post["id"]) \
            .execute()
        
        hashtags = []
        
        if post_hashtags.data and len(post_hashtags.data) > 0:
            hashtag_ids = [ph["hashtag_id"] for ph in post_hashtags.data]
            hashtags_data = db.table("hashtags").select("*").in_("id", hashtag_ids).execute()
            
            if hashtags_data.data:
                hashtags = hashtags_data.data
        
        # Get challenge information if applicable
        challenge_info = None
        if challenge_id:
            challenge_post = db.table("challenge_posts") \
                .select("*") \
                .eq("challenge_id", str(challenge_id)) \
                .eq("post_id", post["id"]) \
                .execute()
            
            if challenge_post.data and len(challenge_post.data) > 0:
                challenge_post_data = challenge_post.data[0]
                
                challenge_data = db.table("challenges") \
                    .select("*") \
                    .eq("id", challenge_post_data["challenge_id"]) \
                    .execute()
                
                if challenge_data.data and len(challenge_data.data) > 0:
                    challenge_info = {
                        "challenge": challenge_data.data[0],
                        "challenge_post_details": challenge_post_data
                    }
        
        post_with_details = {
            **post,
            "user": user,
            "comments_count": comments_count.count if hasattr(comments_count, 'count') else 0,
            "likes_count": likes_count.count if hasattr(likes_count, 'count') else 0,
            "hashtags": hashtags,
            "challenge_info": challenge_info
        }
        
        result.append(post_with_details)
    
    return result 


@router.get("/{post_id}", response_model=PostWithDetails)
def get_post(
    post_id: UUID,
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Get a specific post by ID.
    """
    post_data = db.table("posts").select("*").eq("id", str(post_id)).execute()
    
    if not post_data.data or len(post_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {post_id} not found",
        )
    
    post = post_data.data[0]
    
    # Convert media_urls from string to list
    if "media_urls" in post and isinstance(post["media_urls"], str):
        try:
            # Check if it's PostgreSQL array format (starts with '{' and ends with '}')
            if post["media_urls"].startswith('{') and post["media_urls"].endswith('}'):
                # Parse PostgreSQL array format
                if post["media_urls"] == "{}":
                    post["media_urls"] = []
                else:
                    # Remove the curly braces and split by commas, then remove quotes
                    urls = post["media_urls"][1:-1].split(',')
                    post["media_urls"] = [url.strip('"') for url in urls]
            else:
                # Fallback to JSON parsing for backward compatibility
                post["media_urls"] = json.loads(post["media_urls"])
        except:
            post["media_urls"] = []
    
    # Get user data
    user_data = db.table("users").select("*").eq("id", post["user_id"]).execute()
    
    if user_data.data and len(user_data.data) > 0:
        user = user_data.data[0]
    else:
        user = None
    
    # Get comments count
    comments_count = db.table("comments").select("id", count="exact").eq("post_id", post["id"]).execute()
    
    # Get likes count
    likes_count = db.table("likes").select("id", count="exact").eq("post_id", post["id"]).execute()
    
    # Get hashtags
    post_hashtags = db.table("post_hashtags").select("hashtag_id").eq("post_id", post["id"]).execute()
    
    hashtags = []
    
    if post_hashtags.data and len(post_hashtags.data) > 0:
        hashtag_ids = [ph["hashtag_id"] for ph in post_hashtags.data]
        hashtags_data = db.table("hashtags").select("*").in_("id", hashtag_ids).execute()
        
        if hashtags_data.data:
            hashtags = hashtags_data.data
    
    post_with_details = {
        **post,
        "user": user,
        "comments_count": comments_count.count if hasattr(comments_count, 'count') else 0,
        "likes_count": likes_count.count if hasattr(likes_count, 'count') else 0,
        "hashtags": hashtags,
    }
    
    # Increment view count
    db.table("posts").update({"view_count": post["view_count"] + 1}).eq("id", post["id"]).execute()
    
    return post_with_details


@router.put("/{post_id}", response_model=Post)
async def update_post(
    post_id: UUID,
    post_update: PostUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Update a post.
    """
    # Check if post exists and belongs to user
    post_data = db.table("posts").select("*").eq("id", str(post_id)).execute()
    
    if not post_data.data or len(post_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {post_id} not found",
        )
    
    post = post_data.data[0]
    
    if post["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own posts",
        )
    
    # Prepare update data
    update_data = post_update.model_dump(exclude_unset=True)
    
    if not update_data:
        # Nothing to update
        return Post(**post)
    
    # Moderate content if there are changes to content or media
    if "content" in update_data or "media_urls" in update_data:
        # Get the full content for moderation
        text_to_moderate = update_data.get("content", post["content"])
        
        # For media URLs, use the updated list if provided, otherwise use existing
        if "media_urls" in update_data:
            media_to_moderate = update_data["media_urls"]
        else:
            # Get existing media_urls from post
            media_to_moderate = post.get("media_urls", [])
            if isinstance(media_to_moderate, str):
                try:
                    # Parse PostgreSQL array format if needed
                    if media_to_moderate.startswith('{') and media_to_moderate.endswith('}'):
                        if media_to_moderate == "{}":
                            media_to_moderate = []
                        else:
                            urls = media_to_moderate[1:-1].split(',')
                            media_to_moderate = [url.strip('"') for url in urls]
                    else:
                        # Fallback to JSON parsing
                        media_to_moderate = json.loads(media_to_moderate)
                except:
                    media_to_moderate = []
        
        # Perform moderation check
        moderation_result = await moderate_content(
            text_content=text_to_moderate,
            image_urls=media_to_moderate if media_to_moderate else None
        )
        
        # Check if content was flagged
        if moderation_result.flagged:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content violates community guidelines and cannot be posted",
            )
    
    # Convert media_urls to PostgreSQL array format if it's being updated
    if update_data.get("media_urls") is not None and isinstance(update_data["media_urls"], list):
        if len(update_data["media_urls"]) > 0:
            # Convert to PostgreSQL array format
            update_data["media_urls"] = "{" + ",".join(f'"{url}"' for url in update_data["media_urls"]) + "}"
        else:
            update_data["media_urls"] = "{}"
    
    update_data["updated_at"] = datetime.now().isoformat()
    update_data["edited"] = True
    
    result = db.table("posts").update(update_data).eq("id", str(post_id)).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update post",
        )
    
    updated_post = result.data[0]
    
    # Convert media_urls back to list for response
    if "media_urls" in updated_post and isinstance(updated_post["media_urls"], str):
        try:
            # Check if it's PostgreSQL array format (starts with '{' and ends with '}')
            if updated_post["media_urls"].startswith('{') and updated_post["media_urls"].endswith('}'):
                # Parse PostgreSQL array format
                if updated_post["media_urls"] == "{}":
                    updated_post["media_urls"] = []
                else:
                    # Remove the curly braces and split by commas, then remove quotes
                    urls = updated_post["media_urls"][1:-1].split(',')
                    updated_post["media_urls"] = [url.strip('"') for url in urls]
            else:
                # Fallback to JSON parsing for backward compatibility
                updated_post["media_urls"] = json.loads(updated_post["media_urls"])
        except:
            # Fallback if not valid JSON or array format
            updated_post["media_urls"] = []
    
    return Post(**updated_post)


@router.delete("/{post_id}", response_model=dict)
def delete_post(
    post_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Delete a post.
    """
    # Check if post exists and belongs to the current user
    post_data = db.table("posts").select("*").eq("id", str(post_id)).execute()
    
    if not post_data.data or len(post_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {post_id} not found",
        )
    
    post = post_data.data[0]
    
    if post["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post",
        )
    
    # Delete related entities first (to maintain referential integrity)
    
    # Delete challenge post associations
    db.table("challenge_posts").delete().eq("post_id", str(post_id)).execute()
    
    # Delete likes
    db.table("likes").delete().eq("post_id", str(post_id)).execute()
    
    # Delete comments
    db.table("comments").delete().eq("post_id", str(post_id)).execute()
    
    # Delete saved posts
    db.table("user_saved_posts").delete().eq("post_id", str(post_id)).execute()
    
    # Delete post-hashtag associations
    db.table("post_hashtags").delete().eq("post_id", str(post_id)).execute()
    
    # Delete notifications
    db.table("notifications").delete().eq("post_id", str(post_id)).execute()
    
    # Delete the post
    db.table("posts").delete().eq("id", str(post_id)).execute()
    
    return {"status": "success", "message": "Post deleted successfully"} 


@router.post("/save", response_model=dict)
def save_post(
    save_data: UserSavedPostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Save a post.
    """
    # Check if post exists
    post_data = db.table("posts").select("*").eq("id", str(save_data.post_id)).execute()
    
    if not post_data.data or len(post_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {save_data.post_id} not found",
        )
    
    # Check if already saved
    existing_save = db.table("user_saved_posts") \
        .select("*") \
        .eq("user_id", str(current_user.id)) \
        .eq("post_id", str(save_data.post_id)) \
        .execute()
    
    if existing_save.data and len(existing_save.data) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post already saved",
        )
    
    now = datetime.now().isoformat()
    save_dict = {
        "user_id": str(current_user.id),
        "post_id": str(save_data.post_id),
        "created_at": now,
    }
    
    result = db.table("user_saved_posts").insert(save_dict).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save post",
        )
    
    return {"status": "success", "message": "Post saved successfully"}


@router.delete("/unsave/{post_id}", response_model=dict)
def unsave_post(
    post_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Unsave a post.
    """
    # Check if saved
    saved_post = db.table("user_saved_posts") \
        .select("*") \
        .eq("user_id", str(current_user.id)) \
        .eq("post_id", str(post_id)) \
        .execute()
    
    if not saved_post.data or len(saved_post.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not saved",
        )
    
    # Delete saved post
    db.table("user_saved_posts") \
        .delete() \
        .eq("user_id", str(current_user.id)) \
        .eq("post_id", str(post_id)) \
        .execute()
    
    return {"status": "success", "message": "Post unsaved successfully"} 