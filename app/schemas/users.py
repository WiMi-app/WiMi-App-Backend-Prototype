from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.config import settings


class UserBase(BaseModel):
    """
    Base schema with common user attributes.
    """
    email: EmailStr
    username: str
    full_name: str = Field(
        "", min_length=0, max_length=50, description="User's display name"
    )
    model_config = ConfigDict(from_attributes=True)

class UserOut(UserBase):
    """
    Schema for user data returned by the API.
    Contains all user fields that can be exposed publicly.
    """
    id: str
    avatar_url: Optional[List[str]] = None
    bio: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"))

    @property
    def full_avatar_url(self) -> Optional[str]:
        if self.avatar_url and len(self.avatar_url) == 2:
            bucket_name = self.avatar_url[0]
            file_name = self.avatar_url[1]
            return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket_name}//{file_name}"
        return None

class UserUpdate(BaseModel):
    """
    Schema for updating user profile data.
    Only includes fields that can be updated by the user.
    All fields are optional to allow partial updates.
    """
    username: Optional[str] = None
    full_name: Optional[str] = Field(
        None, min_length=0, max_length=50, description="User's display name"
    )
    bio: Optional[str] = None
    avatar_url: Optional[List[str]] = None
    model_config = ConfigDict(from_attributes=True)
