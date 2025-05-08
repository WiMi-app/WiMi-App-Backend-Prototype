from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ChallengeBase(BaseModel):
    title: str = Field(
        ..., min_length=3, max_length=100, description="Challenge title"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Optional details"
    )
    frequency_days: int = Field(
        ..., ge=1, le=365, description="Repeat interval in days"
    )

class ChallengeCreate(ChallengeBase):
    pass

class ChallengeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    frequency_days: Optional[int] = Field(None, ge=1, le=365)

class ChallengeOut(ChallengeBase):
    id: str
    creator_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
