from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.core.deps import get_current_active_user
from app.db.database import get_supabase
from app.schemas.posts import Post, PostCreate, PostUpdate, PostWithDetails, UserSavedPostCreate
from app.schemas.users import User

router = APIRouter()


@router.post("/", response_model=Post)
def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Create a new post.
    """
    now = datetime.utcnow().isoformat()
    post_dict = post_data.dict()
    post_dict.update({
        "user_id": str(current_user.id),
        "created_at": now,
        "updated_at": now,
    })
    
    result = db.table("posts").insert(post_dict).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post",
        )
    
    # Extract hashtags from content
    content = post_data.content
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
            "post_id": result.data[0]["id"],
            "hashtag_id": hashtag_id,
            "created_at": now,
        }).execute()
    
    return Post(**result.data[0])


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
    
    # Increment view count
    db.table("posts") \
        .update({"view_count": post["view_count"] + 1}) \
        .eq("id", str(post_id)) \
        .execute()
    
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
    
    post_with_details = {
        **post,
        "view_count": post["view_count"] + 1,  # Incremented
        "user": user,
        "comments_count": comments_count.count if hasattr(comments_count, 'count') else 0,
        "likes_count": likes_count.count if hasattr(likes_count, 'count') else 0,
        "hashtags": hashtags,
    }
    
    return PostWithDetails(**post_with_details) 


@router.put("/{post_id}", response_model=Post)
def update_post(
    post_id: UUID,
    post_update: PostUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Update a post.
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
            detail="Not authorized to update this post",
        )
    
    update_data = post_update.dict(exclude_unset=True)
    
    if not update_data:
        return Post(**post)
    
    update_data["updated_at"] = datetime.utcnow().isoformat()
    update_data["edited"] = True
    
    result = db.table("posts").update(update_data).eq("id", str(post_id)).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update post",
        )
    
    return Post(**result.data[0]) 


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
    
    now = datetime.utcnow().isoformat()
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