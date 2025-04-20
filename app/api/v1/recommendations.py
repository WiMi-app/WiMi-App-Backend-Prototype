from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from app.recommendation.models import (
    PostRecommendationRequest,
    ChallengeRecommendationRequest,
    RecommendationResponse
)
from app.recommendation.service import (
    get_post_recommendations,
    get_challenge_recommendations,
    record_post_interaction,
    record_challenge_interaction
)

router = APIRouter()


@router.post("/posts/recommend", response_model=RecommendationResponse)
async def recommend_posts(request: PostRecommendationRequest):
    """Get personalized post recommendations for a user."""
    try:
        recommendations = await get_post_recommendations(request)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get post recommendations: {str(e)}")


@router.post("/challenges/recommend", response_model=RecommendationResponse)
async def recommend_challenges(request: ChallengeRecommendationRequest):
    """Get personalized challenge recommendations for a user."""
    try:
        recommendations = await get_challenge_recommendations(request)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get challenge recommendations: {str(e)}")


@router.post("/posts/{post_id}/interactions/{interaction_type}")
async def record_post_user_interaction(
    post_id: UUID,
    interaction_type: str,
    user_id: UUID
):
    """Record a user's interaction with a post."""
    try:
        if interaction_type not in ["view", "like", "comment", "save", "share"]:
            raise HTTPException(status_code=400, detail="Invalid interaction type")
            
        result = record_post_interaction(
            user_id=user_id,
            post_id=post_id,
            interaction_type=interaction_type
        )
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record post interaction: {str(e)}")


@router.post("/challenges/{challenge_id}/interactions/{interaction_type}")
async def record_challenge_user_interaction(
    challenge_id: UUID,
    interaction_type: str,
    user_id: UUID
):
    """Record a user's interaction with a challenge."""
    try:
        if interaction_type not in ["view", "join", "complete", "share"]:
            raise HTTPException(status_code=400, detail="Invalid interaction type")
            
        result = record_challenge_interaction(
            user_id=user_id,
            challenge_id=challenge_id,
            interaction_type=interaction_type
        )
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record challenge interaction: {str(e)}") 