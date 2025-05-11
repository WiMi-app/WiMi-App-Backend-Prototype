from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PostBase(BaseModel):
    """
    Base schema for post data.
    Contains common post fields used in multiple schemas.
    """
    challenge_id: str = Field(..., description="Associated challenge ID")
    content_url: str = Field(
        ..., min_length=5, description="URL of image/video"
    )

class PostCreate(PostBase):
    """
    Schema for creating a new post.
    Inherits all fields from PostBase.
    """
    pass

class PostUpdate(BaseModel):
    """
    Schema for updating an existing post.
    All fields are optional to allow partial updates.
    """
    content_url: Optional[str] = Field(None, min_length=5)

class PostOut(PostBase):
    """
    Schema for post data returned by the API.
    Contains all fields from PostBase plus system-generated fields.
    """
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
