from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FollowCreate(BaseModel):
    """
    Schema for creating a new follow relationship.
    Only requires the ID of the user to follow.
    """
    followee_id: str = Field(..., description="User ID to follow")

class FollowOut(BaseModel):
    """
    Schema for follow data returned by the API.
    Includes all follow relationship fields including system-generated ones.
    """
    id: str
    follower_id: str
    followee_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
