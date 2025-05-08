from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str = Field(
        "", min_length=0, max_length=50, description="User's display name"
    )

class UserOut(UserBase):
    id: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(
        None, min_length=2, max_length=50
    )
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
