from datetime import datetime
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, validator


class PostBase(BaseModel):
    """
    Base schema for post data.
    Contains common post fields used in multiple schemas.
    """
    content: str = Field(..., description="Post text content")
    model_config = ConfigDict(from_attributes=True)

class PostCreate(BaseModel):
    """
    Schema for creating a new post.
    """
    content: str = Field(..., description="Post text content")
    media_urls: Optional[list[str]] = Field(None, description="URLs of media attachments")
    location: Optional[str] = Field(None, description="Location associated with the post")
    is_private: Optional[bool] = Field(False, description="Whether the post is private")
    challenge_id: Optional[str] = Field(None, description="Associated challenge ID (must be a valid UUID)")
    categories: Optional[list[str]] = Field(None, description="Categories for the post")
    
    @validator('challenge_id')
    def validate_uuid(cls, v):
        if v is None or v == "":
            return None
        try:
            UUID(v)  # Validate it's a proper UUID
            return v
        except ValueError:
            return None  # Return None instead of invalid UUID string

class PostUpdate(BaseModel):
    """
    Schema for updating an existing post.
    All fields are optional to allow partial updates.
    """
    content: Optional[str] = Field(None, description="Post text content")
    media_urls: Optional[list[str]] = Field(None, description="URLs of media attachments")
    location: Optional[str] = Field(None, description="Location associated with the post")
    is_private: Optional[bool] = Field(None, description="Whether the post is private")

class PostOut(BaseModel):
    """
    Schema for post data returned by the API.
    Contains all fields from PostBase plus system-generated fields.
    """
    id: str
    user_id: str
    content: str
    media_urls: Optional[list[str]] = None
    location: Optional[str] = None
    is_private: bool
    created_at: str
    updated_at: str
    edited: bool
    challenge_id: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class SavedPostCreate(BaseModel):
    """
    Schema for saving a post.
    """
    post_id: str = Field(..., description="ID of the post to save")
