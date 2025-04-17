from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from pydantic import BaseModel, EmailStr, Field, HttpUrl, model_validator

BASE_ICON_URL = str(f"{settings.SUPABASE_URL}/storage/v1/object/sign/images/default/icon.png?token={settings.SUPABASE_KEY}")
BASE_COVER_IMAGE_URL = str(f"{settings.SUPABASE_URL}/storage/v1/object/sign/images/default/cover.png?token={settings.SUPABASE_KEY}")

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[HttpUrl] = BASE_ICON_URL
    cover_image_url: Optional[HttpUrl] = BASE_COVER_IMAGE_URL
    
    def model_dump_json_safe(self) -> Dict[str, Any]:
        """Convert model to a dict with URL fields as strings for JSON serialization"""
        data = self.model_dump()
        if data.get("avatar_url") is not None:
            data["avatar_url"] = str(data["avatar_url"])
        if data.get("cover_image_url") is not None:
            data["cover_image_url"] = str(data["cover_image_url"])
        return data


class UserCreate(UserBase):
    password: str
    
    def model_dump_json_safe(self) -> Dict[str, Any]:
        """Convert model to a dict with URL fields as strings for JSON serialization, excluding password"""
        data = super().model_dump_json_safe()
        # Exclude password as it will be stored as password_hash
        if "password" in data:
            del data["password"]
        return data


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[HttpUrl] = BASE_ICON_URL
    cover_image_url: Optional[HttpUrl] = BASE_COVER_IMAGE_URL
    password: Optional[str] = None
    
    def model_dump_json_safe(self) -> Dict[str, Any]:
        """Convert model to a dict with URL fields as strings for JSON serialization"""
        data = self.model_dump(exclude_unset=True)
        if data.get("avatar_url") is not None:
            data["avatar_url"] = str(data["avatar_url"])
        if data.get("cover_image_url") is not None:
            data["cover_image_url"] = str(data["cover_image_url"])
        return data


class UserDB(UserBase):
    id: UUID = Field(default_factory=uuid4)
    password_hash: str
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
    created_challenges_count: int = 0
    joined_challenges_count: int = 0
    achievements_count: int = 0

    class Config:
        from_attributes = True 