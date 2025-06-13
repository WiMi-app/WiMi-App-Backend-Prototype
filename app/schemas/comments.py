from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

class CommentCreate(BaseModel):
    """
    Schema for creating a new comment.
    Requires post_id and content.
    """
    post_id: str = Field(..., description="ID of the post")
    content: str = Field(
        ..., min_length=1, max_length=300, description="Comment text"
    )

class CommentUpdate(BaseModel):
    """
    Schema for updating an existing comment.
    Only content can be updated.
    """
    content: Optional[str] = Field(None, min_length=1, max_length=300)

class CommentOut(BaseModel):
    """
    Schema for comment data returned by the API.
    Includes all comment fields including system-generated ones.
    """
    id: str
    post_id: str
    user_id: str
    content: str
    created_at: datetime
    parent_comment_id: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v):
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                return None
        return v