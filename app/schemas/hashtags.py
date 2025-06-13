from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class HashtagOut(BaseModel):
    """
    Schema for hashtag data returned by the API.
    Includes hashtag properties and usage statistics.
    """
    id: str
    tag: str = Field(..., min_length=1, max_length=50)
    usage_count: int = Field(..., ge=0)
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    
