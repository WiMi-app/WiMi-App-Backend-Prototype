"""Recommendation service for WiMi app."""
from uuid import UUID
from typing import List, Dict, Any
from datetime import datetime

from app.db.database import supabase
from app.recommendation.models import (
    PostRecommendationRequest,
    ChallengeRecommendationRequest,
    RecommendationResponse
)
from app.recommendation.schemas import (
    USER_INTERESTS_TABLE,
    POST_CATEGORIES_TABLE,
    CHALLENGE_CATEGORIES_TABLE,
    USER_POST_INTERACTIONS_TABLE,
    USER_CHALLENGE_INTERACTIONS_TABLE,
    RECOMMENDATION_LOGS_TABLE,
    log_recommendation
)

async def get_post_recommendations(request: PostRecommendationRequest) -> RecommendationResponse:
    """Get personalized post recommendations for a user."""
    user_id = request.user_id
    limit = request.limit
    offset = request.offset
    
    # Get user interests
    user_interests = supabase.table(USER_INTERESTS_TABLE)\
        .select("*")\
        .eq("user_id", str(user_id))\
        .execute()
    
    interest_categories = [interest["category"] for interest in user_interests.data]
    
    # Base query for posts with categories
    query = supabase.table("posts")\
        .select(
            "id:post_id, user_id:creator_id, title, description, created_at, media_urls, like_count, comment_count, categories:post_categories(category, confidence)"
        )\
        .eq("is_deleted", False)\
        .order("created_at", desc=True)
    
    # Filter by user's interests if available
    if interest_categories and len(interest_categories) > 0:
        # This is a simplified approach - in a real system, you would use a more sophisticated 
        # algorithm and potentially join with post_categories for better filtering
        query = query.in_("post_categories.category", interest_categories)
    
    # Exclude posts the user has already seen if requested
    if request.exclude_seen:
        seen_posts_query = supabase.table(USER_POST_INTERACTIONS_TABLE)\
            .select("post_id")\
            .eq("user_id", str(user_id))\
            .eq("interaction_type", "view")\
            .execute()
        
        seen_post_ids = [item["post_id"] for item in seen_posts_query.data]
        
        if seen_post_ids:
            query = query.not_.in_("id", seen_post_ids)
    
    # Execute the query with pagination
    result = query.range(offset, offset + limit - 1).execute()
    
    # Process results and log recommendations
    items = []
    for post in result.data:
        # Simple scoring based on recency and category match (can be enhanced)
        score = 1.0  # Base score
        
        # Log this recommendation
        log_recommendation(
            user_id=user_id,
            content_id=UUID(post["id"]),
            content_type="post",
            score=score,
            was_shown=True
        )
        
        # Add to results
        items.append(post)
    
    return RecommendationResponse(
        items=items,
        total=len(result.data)
    )

async def get_challenge_recommendations(request: ChallengeRecommendationRequest) -> RecommendationResponse:
    """Get personalized challenge recommendations for a user."""
    user_id = request.user_id
    limit = request.limit
    offset = request.offset
    
    # Get user interests
    user_interests = supabase.table(USER_INTERESTS_TABLE)\
        .select("*")\
        .eq("user_id", str(user_id))\
        .execute()
    
    interest_categories = [interest["category"] for interest in user_interests.data]
    
    # Base query for challenges with categories
    query = supabase.table("challenges")\
        .select(
            "id:challenge_id, user_id:creator_id, title, description, created_at, media_urls, participant_count, categories:challenge_categories(category, confidence)"
        )\
        .eq("is_deleted", False)\
        .order("created_at", desc=True)
    
    # Filter by user's interests if available
    if interest_categories and len(interest_categories) > 0:
        query = query.in_("challenge_categories.category", interest_categories)
    
    # Exclude challenges the user has already joined if requested
    if request.exclude_joined:
        joined_challenges_query = supabase.table(USER_CHALLENGE_INTERACTIONS_TABLE)\
            .select("challenge_id")\
            .eq("user_id", str(user_id))\
            .eq("interaction_type", "join")\
            .execute()
        
        joined_challenge_ids = [item["challenge_id"] for item in joined_challenges_query.data]
        
        if joined_challenge_ids:
            query = query.not_.in_("id", joined_challenge_ids)
    
    # Execute the query with pagination
    result = query.range(offset, offset + limit - 1).execute()
    
    # Process results and log recommendations
    items = []
    for challenge in result.data:
        # Simple scoring based on recency and category match (can be enhanced)
        score = 1.0  # Base score
        
        # Log this recommendation
        log_recommendation(
            user_id=user_id,
            content_id=UUID(challenge["id"]),
            content_type="challenge",
            score=score,
            was_shown=True
        )
        
        # Add to results
        items.append(challenge)
    
    return RecommendationResponse(
        items=items,
        total=len(result.data)
    )

def record_post_interaction(
    user_id: UUID, 
    post_id: UUID, 
    interaction_type: str
) -> Dict:
    """Record a user's interaction with a post and update recommendation weights."""
    # Determine interaction weight based on interaction type
    interaction_weights = {
        "view": 1.0,
        "like": 3.0,
        "comment": 4.0,
        "save": 5.0,
        "share": 6.0
    }
    
    interaction_weight = interaction_weights.get(interaction_type, 1.0)
    
    # Record interaction
    data = {
        "user_id": str(user_id),
        "post_id": str(post_id),
        "interaction_type": interaction_type,
        "interaction_weight": interaction_weight,
        "created_at": datetime.now().isoformat()
    }
    
    result = supabase.table(USER_POST_INTERACTIONS_TABLE).insert(data).execute()
    
    # Update recommendation log if exists
    supabase.table(RECOMMENDATION_LOGS_TABLE)\
        .update({"was_clicked": True})\
        .eq("user_id", str(user_id))\
        .eq("content_id", str(post_id))\
        .eq("content_type", "post")\
        .execute()
    
    # Optionally: Update user interests based on post categories
    post_categories = supabase.table(POST_CATEGORIES_TABLE)\
        .select("category")\
        .eq("post_id", str(post_id))\
        .execute()
    
    for category_data in post_categories.data:
        category = category_data["category"]
        
        # Check if user already has this interest
        existing_interest = supabase.table(USER_INTERESTS_TABLE)\
            .select("*")\
            .eq("user_id", str(user_id))\
            .eq("category", category)\
            .execute()
        
        if existing_interest.data:
            # Update weight
            interest = existing_interest.data[0]
            new_weight = min(interest["weight"] + (interaction_weight * 0.1), 10.0)
            
            supabase.table(USER_INTERESTS_TABLE)\
                .update({"weight": new_weight, "updated_at": datetime.now().isoformat()})\
                .eq("id", interest["id"])\
                .execute()
        else:
            # Create new interest
            supabase.table(USER_INTERESTS_TABLE)\
                .insert({
                    "user_id": str(user_id),
                    "category": category,
                    "weight": interaction_weight * 0.2,  # Initial weight based on interaction
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                })\
                .execute()
    
    return result.data[0] if result.data else None

def record_challenge_interaction(
    user_id: UUID, 
    challenge_id: UUID, 
    interaction_type: str
) -> Dict:
    """Record a user's interaction with a challenge and update recommendation weights."""
    # Determine interaction weight based on interaction type
    interaction_weights = {
        "view": 1.0,
        "join": 5.0,
        "complete": 8.0,
        "share": 6.0
    }
    
    interaction_weight = interaction_weights.get(interaction_type, 1.0)
    
    # Record interaction
    data = {
        "user_id": str(user_id),
        "challenge_id": str(challenge_id),
        "interaction_type": interaction_type,
        "interaction_weight": interaction_weight,
        "created_at": datetime.now().isoformat()
    }
    
    result = supabase.table(USER_CHALLENGE_INTERACTIONS_TABLE).insert(data).execute()
    
    # Update recommendation log if exists
    supabase.table(RECOMMENDATION_LOGS_TABLE)\
        .update({"was_clicked": True})\
        .eq("user_id", str(user_id))\
        .eq("content_id", str(challenge_id))\
        .eq("content_type", "challenge")\
        .execute()
    
    # Optionally: Update user interests based on challenge categories
    challenge_categories = supabase.table(CHALLENGE_CATEGORIES_TABLE)\
        .select("category")\
        .eq("challenge_id", str(challenge_id))\
        .execute()
    
    for category_data in challenge_categories.data:
        category = category_data["category"]
        
        # Check if user already has this interest
        existing_interest = supabase.table(USER_INTERESTS_TABLE)\
            .select("*")\
            .eq("user_id", str(user_id))\
            .eq("category", category)\
            .execute()
        
        if existing_interest.data:
            # Update weight
            interest = existing_interest.data[0]
            new_weight = min(interest["weight"] + (interaction_weight * 0.1), 10.0)
            
            supabase.table(USER_INTERESTS_TABLE)\
                .update({"weight": new_weight, "updated_at": datetime.now().isoformat()})\
                .eq("id", interest["id"])\
                .execute()
        else:
            # Create new interest
            supabase.table(USER_INTERESTS_TABLE)\
                .insert({
                    "user_id": str(user_id),
                    "category": category,
                    "weight": interaction_weight * 0.2,  # Initial weight based on interaction
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                })\
                .execute()
    
    return result.data[0] if result.data else None 