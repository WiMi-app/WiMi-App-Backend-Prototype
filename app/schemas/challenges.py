from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ChallengeBase(BaseModel):
    """
    Base schema for challenge data.
    Contains common challenge fields used in multiple schemas.
    """
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
    """
    Schema for creating a new challenge.
    Inherits all fields from ChallengeBase.
    """
    pass

class ChallengeUpdate(BaseModel):
    """
    Schema for updating an existing challenge.
    All fields are optional to allow partial updates.
    """
    title: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    frequency_days: Optional[int] = Field(None, ge=1, le=365)

class ChallengeOut(ChallengeBase):
    """
    Schema for challenge data returned by the API.
    Contains all fields from ChallengeBase plus system-generated fields.
    """
    id: str
    creator_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
