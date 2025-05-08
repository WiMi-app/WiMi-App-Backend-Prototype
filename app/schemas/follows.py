from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class FollowCreate(BaseModel):
    followee_id: str = Field(..., description="User ID to follow")

class FollowOut(BaseModel):
    id: str
    follower_id: str
    followee_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
