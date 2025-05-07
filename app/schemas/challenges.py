from datetime import datetime, time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.users import User
from app.schemas.posts import Post

'''CHALLENGES'''
class ChallengeBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    due_date: Optional[datetime] = None
    location: Optional[str] = None
    restriction: Optional[str] = None
    repetition: str = Field(..., pattern='^(daily|weekly|monthly|custom|none)$')
    repetition_frequency: Optional[int] = Field(None, ge=1)  # Must be positive if provided
    repetition_days: Optional[List[int]] = Field(None, min_items=1)  # Must have at least one day if provided
    check_in_time: time
    is_private: bool = False
    time_window: int = Field(..., ge=1)  # Grace period in minutes, must be positive

    @field_validator('repetition_days')
    def validate_repetition_days(cls, v, values):
        if v is not None:
            if values.get('repetition') != 'weekly':
                raise ValueError('repetition_days can only be set for weekly repetition')
            if not all(1 <= day <= 7 for day in v):
                raise ValueError('repetition_days must be between 1 and 7')
        return v

    @field_validator('repetition_frequency')
    def validate_repetition_frequency(cls, v, values):
        if v is not None:
            if values.get('repetition') == 'none':
                raise ValueError('repetition_frequency cannot be set for no repetition')
            if v < 1:
                raise ValueError('repetition_frequency must be positive')
        return v


class ChallengeCreate(ChallengeBase):
    pass


class ChallengeUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    location: Optional[str] = None
    restriction: Optional[str] = None
    repetition: Optional[str] = Field(None, pattern='^(daily|weekly|monthly|custom|none)$')
    repetition_frequency: Optional[int] = Field(None, ge=1)
    repetition_days: Optional[List[int]] = Field(None, min_items=1)
    check_in_time: Optional[time] = None
    is_private: Optional[bool] = None
    time_window: Optional[int] = Field(None, ge=1)


class Challenge(ChallengeBase):
    id: UUID
    creator_id: UUID
    created_at: datetime
    updated_at: datetime
    

    class Config:
        from_attributes = True


'''Challenge Participants'''
class ChallengeParticipantCreate(BaseModel):
    challenge_id: UUID


class ChallengeParticipant(BaseModel):
    challenge_id: UUID
    user_id: UUID
    joined_at: datetime
    status: str = Field("active", pattern='^(active|completed|dropped)$')

    class Config:
        from_attributes = True


class ChallengePostCreate(BaseModel):
    challenge_id: UUID
    post_id: UUID
    is_check_in: bool = True


class ChallengePost(BaseModel):
    challenge_id: UUID
    post_id: UUID
    is_check_in: bool
    submitted_at: datetime

    class Config:
        from_attributes = True


class ChallengeWithDetails(Challenge):
    creator: User
    participant_count: int = 0
    posts_count: int = 0
    is_joined: bool = False

    class Config:
        from_attributes = True

'''Challenge Achievments'''
class ChallengeAchievementCreate(BaseModel):
    challenge_id: UUID
    user_id: UUID
    achievement_type: str = Field(..., pattern='^(success_rate|completion)$')
    description: str
    success_count: Optional[int] = Field(None, ge=0)  # Must be non-negative if provided


class ChallengeAchievement(BaseModel):
    id: UUID
    challenge_id: UUID
    user_id: UUID
    achievement_type: str = Field(..., pattern='^(success_rate|completion)$')
    description: str
    achieved_at: datetime
    success_count: Optional[int] = Field(None, ge=0)

    class Config:
        from_attributes = True 