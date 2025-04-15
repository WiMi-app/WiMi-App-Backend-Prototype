from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, HttpUrl

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    cover_image_url: Optional[HttpUrl] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    cover_image_url: Optional[HttpUrl] = None
    password: Optional[str] = None


class UserDB(UserBase):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class User(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserWithStats(User):
    posts_count: int = 0
    followers_count: int = 0
    following_count: int = 0

    class Config:
        from_attributes = True 