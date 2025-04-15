from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FollowBase(BaseModel):
    followed_id: UUID


class FollowCreate(FollowBase):
    pass


class Follow(FollowBase):
    id: UUID
    follower_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True 