from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator
from fastapi import HTTPException


class LikeBase(BaseModel):
    pass


class LikeCreate(LikeBase):
    post_id: Optional[UUID] = None
    comment_id: Optional[UUID] = None


class Like(LikeBase):
    id: UUID
    user_id: UUID
    post_id: Optional[UUID] = None
    comment_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True 