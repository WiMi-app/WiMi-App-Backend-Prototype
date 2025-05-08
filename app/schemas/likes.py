from pydantic import BaseModel, Field
from datetime import datetime

class LikeCreate(BaseModel):
    post_id: str = Field(..., description="ID of the post to like")

class LikeOut(BaseModel):
    id: str
    post_id: str
    user_id: str
    created_at: datetime

    class Config:
        orm_mode = True
