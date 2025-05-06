from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class HashtagBase(BaseModel):
    name: str


class HashtagCreate(HashtagBase):
    pass


class Hashtag(HashtagBase):
    id: UUID
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class PostHashtagCreate(BaseModel):
    post_id: UUID
    hashtag_id: UUID


class PostHashtag(PostHashtagCreate):
    created_at: datetime

    class Config:
        from_attributes = True 