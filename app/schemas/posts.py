from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, HttpUrl, Field

from app.schemas.users import User
from app.schemas.hashtags import Hashtag


class PostBase(BaseModel):
    content: str
    media_urls: Optional[List[str]] = []
    location: Optional[str] = None
    is_private: bool = False


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    content: Optional[str] = None
    media_urls: Optional[List[str]] = None
    location: Optional[str] = None
    is_private: Optional[bool] = None


class Post(PostBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    edited: bool = False
    view_count: int = 0

    class Config:
        from_attributes = True


class PostWithUserInfo(Post):
    user: User

    class Config:
        from_attributes = True


class PostWithDetails(Post):
    user: User
    comments_count: int = 0
    likes_count: int = 0
    hashtags: List[Hashtag] = []

    class Config:
        from_attributes = True


class UserSavedPostCreate(BaseModel):
    post_id: UUID


class UserSavedPost(BaseModel):
    user_id: UUID
    post_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class FeedItem(BaseModel):
    post: PostWithDetails
    is_liked: bool = False
    is_saved: bool = False

    class Config:
        from_attributes = True 