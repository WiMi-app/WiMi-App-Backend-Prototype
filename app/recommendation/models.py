from pydantic import BaseModel, UUID4
from typing import List, Optional, Dict, Any
from datetime import datetime


class UserInterest(BaseModel):
    id: Optional[UUID4] = None
    user_id: UUID4
    category: str
    weight: float = 1.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PostCategory(BaseModel):
    id: Optional[UUID4] = None
    post_id: UUID4
    category: str
    confidence: float = 1.0
    created_at: Optional[datetime] = None


class ChallengeCategory(BaseModel):
    id: Optional[UUID4] = None
    challenge_id: UUID4
    category: str
    confidence: float = 1.0
    created_at: Optional[datetime] = None


class UserPostInteraction(BaseModel):
    id: Optional[UUID4] = None
    user_id: UUID4
    post_id: UUID4
    interaction_type: str  # 'view', 'like', 'comment', 'save', 'share'
    interaction_weight: float = 1.0
    created_at: Optional[datetime] = None


class UserChallengeInteraction(BaseModel):
    id: Optional[UUID4] = None
    user_id: UUID4
    challenge_id: UUID4
    interaction_type: str  # 'view', 'join', 'complete', 'share'
    interaction_weight: float = 1.0
    created_at: Optional[datetime] = None


class RecommendationLog(BaseModel):
    id: Optional[UUID4] = None
    user_id: UUID4
    content_id: UUID4
    content_type: str  # 'post' or 'challenge'
    score: float
    was_shown: bool = False
    was_clicked: bool = False
    created_at: Optional[datetime] = None


class PostRecommendationRequest(BaseModel):
    user_id: UUID4
    limit: int = 10
    offset: int = 0
    include_following: bool = True
    include_global: bool = True
    exclude_seen: bool = True


class ChallengeRecommendationRequest(BaseModel):
    user_id: UUID4
    limit: int = 10
    offset: int = 0
    include_followed_creators: bool = True
    include_global: bool = True
    exclude_joined: bool = True


class RecommendationResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int 