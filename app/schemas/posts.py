from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class PostBase(BaseModel):
    challenge_id: str = Field(..., description="Associated challenge ID")
    content_url: str = Field(
        ..., min_length=5, description="URL of image/video"
    )

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    content_url: Optional[str] = Field(None, min_length=5)

class PostOut(PostBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
