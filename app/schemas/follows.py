from pydantic import BaseModel, Field
from datetime import datetime

class FollowCreate(BaseModel):
    followee_id: str = Field(..., description="User ID to follow")

class FollowOut(BaseModel):
    id: str
    follower_id: str
    followee_id: str
    created_at: datetime

    class Config:
        orm_mode = True
