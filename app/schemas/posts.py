from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    media_urls: Optional[List[List[str]]] = Field(None, description="List of [bucket, filename] for media attachments")
    location: Optional[str] = Field(None, description="Location associated with the post")
    is_private: Optional[bool] = Field(False, description="Whether the post is private")
    challenge_id: Optional[str] = Field(None, description="Associated challenge ID (must be a valid UUID)")
    categories: Optional[list[str]] = Field(None, description="Categories for the post")
    
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
    media_urls: Optional[List[List[str]]] = Field(None, description="List of [bucket, filename] for media attachments")
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
        for item_str in self.media_urls:
            if not (isinstance(item_str, str) and item_str.startswith('{') and item_str.endswith('}')):
                print(f"Skipping malformed media_url item string: {item_str}")
                continue

            content = item_str[1:-1]
            
            parts = []
            current_element = ""
            in_quotes = False
            escape_next = False
            
            for char_idx, char in enumerate(content):
                if escape_next:
                    current_element += char
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and (char_idx == 0 or content[char_idx-1] != '\\'):
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    parts.append(current_element)
                    current_element = ""
                else:
                    current_element += char
            parts.append(current_element)

            if len(parts) == 2:
                bucket_name = parts[0].strip()
                file_name = parts[1].strip()

                if bucket_name.startswith('"') and bucket_name.endswith('"'):
                    bucket_name = bucket_name[1:-1].replace('\\"' ,'"')
                if file_name.startswith('"') and file_name.endswith('"'):
                    file_name = file_name[1:-1].replace('\\"' ,'"')

                processed_urls.append(f"https://vnxbcytjkzpmcdjkmkba.supabase.co/storage/v1/object/public/{bucket_name}/{file_name}")
            else:
                print(f"Could not parse media_url item '{item_str}' into two parts. Parsed: {parts}")
                
        return processed_urls if processed_urls else None

class SavedPostCreate(BaseModel):
    """
    Schema for saving a post.
    """
    post_id: str = Field(..., description="ID of the post to save")
