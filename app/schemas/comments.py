from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.users import User


class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    post_id: UUID
    parent_comment_id: Optional[UUID] = None


class CommentUpdate(BaseModel):
    content: str


class Comment(CommentBase):
    id: UUID
    post_id: UUID
    user_id: UUID
    parent_comment_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommentWithUserInfo(Comment):
    user: User

    class Config:
        from_attributes = True 