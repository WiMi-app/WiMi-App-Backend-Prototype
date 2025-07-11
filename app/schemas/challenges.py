import json
from datetime import datetime, time
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings


class RepetitionType(str, Enum):
    """Enum for challenge repetition types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ParticipationStatus(str, Enum):
    """Enum for challenge participation status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"


class ChallengeBase(BaseModel):
    """
    Base schema for challenge data.
    Contains common challenge fields used in multiple schemas.
    """
    title: str = Field(
        ..., min_length=3, max_length=255, description="Challenge title"
    )
    description: str = Field(
        "", description="Challenge details"
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
    check_in_time: Optional[time] = Field(
        None, description="Local time of day for check-ins (e.g., 09:00:00)"
    )
    is_private: bool = Field(
        False, description="Whether the challenge is private"
    )
    time_window: Optional[int] = Field(
        None, description="Time window for challenge completion in minutes"
    )
    background_photo: Optional[List[str]] = Field(
        None, description="[bucket, filename] for the challenge background photo"
    )
    embedding: Optional[List[float]] = Field(
        None, description="vector value for vector search"
    )
    @field_validator("due_date", mode="before")
    @classmethod
    def parse_due_date(cls, v):
        if isinstance(v, str):
            try:
                # Handle Supabase's non-standard timezone format (+00)
                if v.endswith("+00"):
                    v_fixed = v + ":00"
                    return datetime.fromisoformat(v_fixed)
                return datetime.fromisoformat(v)
            except ValueError:
                return None
        return v
        
    @field_validator("embedding", mode="before")
    @classmethod
    def parse_embedding(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

class ChallengeCreate(ChallengeBase):
    """
    Schema for creating a new challenge.
    Inherits all fields from ChallengeBase.
    """
    user_timezone: str = Field(..., description="User's current timezone (e.g., 'America/New_York')")


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
    check_in_time: Optional[time] = Field(None)
    is_private: Optional[bool] = Field(None)
    time_window: Optional[int] = Field(None)
    background_photo: Optional[List[str]] = Field(None, description="[bucket, filename] for the challenge background photo")
    

class ChallengeOut(ChallengeBase):
    """
    Schema for challenge data returned by the API.
    Contains all fields from ChallengeBase plus system-generated fields.
    """
    id: str
    creator_id: str
    created_at: str
    updated_at: str
    scheduler_job_ids: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True)

    @property
    def full_background_photo_url(self) -> Optional[str]:
        if self.background_photo and isinstance(self.background_photo, list) and len(self.background_photo) == 2:
            bucket_name, file_name = self.background_photo
            # Bucket name for background_photo is "background_photo"
            return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket_name}//{file_name}"
        return None


class ChallengeParticipantOut(BaseModel):
    """
    Schema for challenge participant data returned by the API.
    """
    challenge_id: str
    user_id: str
    joined_at: str
    status: ParticipationStatus
    success_rate: float = Field(0.0, description="Participant's success rate")
    streaks: int = Field(0, description="Participant's current streak")
    count: int = Field(0, description="Participant's total success count")
    model_config = ConfigDict(from_attributes=True)
