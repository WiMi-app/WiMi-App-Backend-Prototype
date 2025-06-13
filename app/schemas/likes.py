from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

class LikeCreate(BaseModel):
    """
    Schema for creating a new like.
    Only requires the post_id to like.
    """
    post_id: str = Field(..., description="ID of the post to like")

class LikeOut(BaseModel):
    """
    Schema for like data returned by the API.
    Includes all like fields including system-generated ones.
    """
    id: str
    post_id: str
    user_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v