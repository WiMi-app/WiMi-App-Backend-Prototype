"""Database schemas for recommendation models."""
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.db.database import supabase

# Tables
USER_INTERESTS_TABLE = "user_interests"
POST_CATEGORIES_TABLE = "post_categories"
CHALLENGE_CATEGORIES_TABLE = "challenge_categories"
USER_POST_INTERACTIONS_TABLE = "user_post_interactions"
USER_CHALLENGE_INTERACTIONS_TABLE = "user_challenge_interactions"
RECOMMENDATION_LOGS_TABLE = "recommendation_logs"

# Create user interest
def create_user_interest(user_id: UUID, category: str, weight: float = 1.0) -> Dict:
    """Create a new user interest record."""
    now = datetime.now().isoformat()
    
    data = {
        "id": str(uuid4()),
        "user_id": str(user_id),
        "category": category,
        "weight": weight,
        "created_at": now,
        "updated_at": now
    }
    
    result = supabase.table(USER_INTERESTS_TABLE).insert(data).execute()
    return result.data[0] if result.data else None

# Update user interest
def update_user_interest(interest_id: UUID, weight: float) -> Dict:
    """Update a user interest's weight."""
    data = {
        "weight": weight,
        "updated_at": datetime.now().isoformat()
    }
    
    result = supabase.table(USER_INTERESTS_TABLE).update(data).eq("id", str(interest_id)).execute()
    return result.data[0] if result.data else None

# Create post category
def create_post_category(post_id: UUID, category: str, confidence: float = 1.0) -> Dict:
    """Create a post category record."""
    data = {
        "id": str(uuid4()),
        "post_id": str(post_id),
        "category": category,
        "confidence": confidence,
        "created_at": datetime.now().isoformat()
    }
    
    result = supabase.table(POST_CATEGORIES_TABLE).insert(data).execute()
    return result.data[0] if result.data else None

# Create challenge category
def create_challenge_category(challenge_id: UUID, category: str, confidence: float = 1.0) -> Dict:
    """Create a challenge category record."""
    data = {
        "id": str(uuid4()),
        "challenge_id": str(challenge_id),
        "category": category,
        "confidence": confidence,
        "created_at": datetime.now().isoformat()
    }
    
    result = supabase.table(CHALLENGE_CATEGORIES_TABLE).insert(data).execute()
    return result.data[0] if result.data else None

# Create user post interaction
def create_user_post_interaction(
    user_id: UUID, 
    post_id: UUID, 
    interaction_type: str, 
    interaction_weight: float = 1.0
) -> Dict:
    """Create a user post interaction record."""
    data = {
        "id": str(uuid4()),
        "user_id": str(user_id),
        "post_id": str(post_id),
        "interaction_type": interaction_type,
        "interaction_weight": interaction_weight,
        "created_at": datetime.now().isoformat()
    }
    
    result = supabase.table(USER_POST_INTERACTIONS_TABLE).insert(data).execute()
    return result.data[0] if result.data else None

# Create user challenge interaction
def create_user_challenge_interaction(
    user_id: UUID, 
    challenge_id: UUID, 
    interaction_type: str, 
    interaction_weight: float = 1.0
) -> Dict:
    """Create a user challenge interaction record."""
    data = {
        "id": str(uuid4()),
        "user_id": str(user_id),
        "challenge_id": str(challenge_id),
        "interaction_type": interaction_type,
        "interaction_weight": interaction_weight,
        "created_at": datetime.now().isoformat()
    }
    
    result = supabase.table(USER_CHALLENGE_INTERACTIONS_TABLE).insert(data).execute()
    return result.data[0] if result.data else None

# Log recommendation
def log_recommendation(
    user_id: UUID,
    content_id: UUID, 
    content_type: str, 
    score: float, 
    was_shown: bool = False
) -> Dict:
    """Log a recommendation."""
    data = {
        "id": str(uuid4()),
        "user_id": str(user_id),
        "content_id": str(content_id),
        "content_type": content_type,
        "score": score,
        "was_shown": was_shown,
        "was_clicked": False,
        "created_at": datetime.now().isoformat()
    }
    
    result = supabase.table(RECOMMENDATION_LOGS_TABLE).insert(data).execute()
    return result.data[0] if result.data else None

# Update recommendation log when clicked
def update_recommendation_log_clicked(log_id: UUID) -> Dict:
    """Update a recommendation log when it's clicked."""
    data = {
        "was_clicked": True
    }
    
    result = supabase.table(RECOMMENDATION_LOGS_TABLE).update(data).eq("id", str(log_id)).execute()
    return result.data[0] if result.data else None 