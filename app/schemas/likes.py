from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, validator
from fastapi import HTTPException


class LikeBase(BaseModel):
    pass


class LikeCreate(LikeBase):
    post_id: Optional[UUID] = None
    comment_id: Optional[UUID] = None

    @validator('comment_id')
    def validate_target(cls, comment_id, values):
        post_id = values.get('post_id')
        if post_id is not None and comment_id is not None:
            raise HTTPException(status_code=400, detail="Cannot like both post and comment at the same time")
        if post_id is None and comment_id is None:
            raise HTTPException(status_code=400, detail="Must like either a post or a comment")
        return comment_id


class Like(LikeBase):
    id: UUID
    user_id: UUID
    post_id: Optional[UUID] = None
    comment_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True 