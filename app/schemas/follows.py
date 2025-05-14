from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FollowCreate(BaseModel):
    """
    Schema for creating a new follow relationship.
    Accepts either followed_id or followee_id (for backward compatibility).
    """
    followed_id: Optional[str] = Field(None, description="User ID to follow (preferred field name)")
    followee_id: Optional[str] = Field(None, description="User ID to follow (legacy field name)")
    
    @model_validator(mode='after')
    def ensure_id_field(self):
        # If followed_id is not set but followee_id is, copy value to followed_id
        if self.followed_id is None and self.followee_id is not None:
            self.followed_id = self.followee_id
            
        # Ensure at least one of the fields is set
        if self.followed_id is None:
            raise ValueError("Either 'followed_id' or 'followee_id' is required")
            
        return self

class FollowOut(BaseModel):
    """
    Schema for follow data returned by the API.
    Includes all follow relationship fields including system-generated ones.
    """
    id: str
    follower_id: str
    followed_id: str
    created_at: str
    model_config = ConfigDict(from_attributes=True)
