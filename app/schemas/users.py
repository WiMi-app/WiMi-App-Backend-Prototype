from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"))

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
    avatar_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
