from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class CommentCreate(BaseModel):
    post_id: str = Field(..., description="ID of the post")
    content: str = Field(
        ..., min_length=1, max_length=300, description="Comment text"
    )

class CommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=300)

class CommentOut(BaseModel):
    id: str
    post_id: str
    user_id: str
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
