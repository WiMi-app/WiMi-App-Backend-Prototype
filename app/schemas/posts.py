from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings


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
    media_urls: Optional[List[str]] = Field(None, description="List of [bucket, filename] for media attachments")
    location: Optional[str] = Field(None, description="Location associated with the post")
    is_private: Optional[bool] = Field(False, description="Whether the post is private")
    challenge_id: Optional[str] = Field(None, description="Associated challenge ID (must be a valid UUID)")
    
    @field_validator('challenge_id')
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
    media_urls: Optional[List[str]] = Field(None, description="List of [bucket, filename] for media attachments")
    location: Optional[str] = Field(None, description="Location associated with the post")
    is_private: Optional[bool] = Field(None, description="Whether the post is private")

class PostEndorsementInfo(BaseModel):
    """
    Schema for post endorsement information.
    """
    is_endorsed: bool = Field(False, description="Whether the post is fully endorsed")
    endorsement_count: int = Field(0, description="Number of endorsements received")
    pending_endorsement_count: int = Field(0, description="Number of pending endorsements")
    endorser_ids: List[str] = Field([], description="IDs of users who have endorsed the post")
    model_config = ConfigDict(from_attributes=True)

class PostOut(BaseModel):
    """
    Schema for post data returned by the API.
    Contains all fields from PostBase plus system-generated fields.
    """
    id: str
    user_id: str
    content: str
    media_urls: Optional[List[str]] = None
    location: Optional[str] = None
    is_private: bool
    created_at: str
    updated_at: str
    edited: bool
    challenge_id: Optional[str] = None
    is_endorsed: bool = False
    endorsement_info: Optional[PostEndorsementInfo] = None
    model_config = ConfigDict(from_attributes=True)

    @property
    def full_media_urls(self) -> Optional[List[str]]:
        if not self.media_urls:
            return None
        
        processed_urls = []
        for item in self.media_urls:
            if isinstance(item, list) and len(item) == 2:
                bucket, path = item
                processed_urls.append(f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}//{path}")
        return processed_urls

class SavedPostCreate(BaseModel):
    """
    Schema for saving a post.
    """
    post_id: str = Field(..., description="ID of the post to save")
