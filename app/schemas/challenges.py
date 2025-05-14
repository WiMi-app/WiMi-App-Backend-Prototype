from datetime import datetime, time
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RepetitionType(str, Enum):
    """Enum for challenge repetition types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ChallengeBase(BaseModel):
    """
    Base schema for challenge data.
    Contains common challenge fields used in multiple schemas.
    """
    title: str = Field(
        ..., min_length=3, max_length=255, description="Challenge title"
    )
    description: Optional[str] = Field(
        None, description="Optional challenge details"
    )
    due_date: Optional[datetime] = Field(
        None, description="When the challenge ends"
    )
    location: Optional[str] = Field(
        None, description="Location for the challenge"
    )
    restriction: Optional[str] = Field(
        None, description="Any restrictions for the challenge"
    )
    repetition: Optional[RepetitionType] = Field(
        None, description="How often the challenge repeats"
    )
    repetition_frequency: Optional[int] = Field(
        None, description="Frequency of repetition"
    )
    repetition_days: Optional[List[int]] = Field(
        None, description="Days on which the challenge repeats (e.g., [1,3,5] for Mon, Wed, Fri)"
    )
    check_in_time: Optional[time] = Field(
        None, description="Time of day for check-ins"
    )
    is_private: Optional[bool] = Field(
        False, description="Whether the challenge is private"
    )
    time_window: Optional[int] = Field(
        None, description="Time window for challenge completion in minutes"
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
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None)
    due_date: Optional[datetime] = Field(None)
    location: Optional[str] = Field(None)
    restriction: Optional[str] = Field(None)
    repetition: Optional[RepetitionType] = Field(None)
    repetition_frequency: Optional[int] = Field(None)
    repetition_days: Optional[List[int]] = Field(None)
    check_in_time: Optional[time] = Field(None)
    is_private: Optional[bool] = Field(None)
    time_window: Optional[int] = Field(None)


class ChallengeOut(ChallengeBase):
    """
    Schema for challenge data returned by the API.
    Contains all fields from ChallengeBase plus system-generated fields.
    """
    id: str
    creator_id: str
    created_at: str
    updated_at: str
    model_config = ConfigDict(from_attributes=True)
