from datetime import datetime, time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, HttpUrl, Field

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
    repetition_frequency: Optional[int] = None  # e.g., 3 for "every 3 days"
    repetition_days: Optional[List[int]] = None  # For weekly challenges: [1,3,5] for Mon,Wed,Fri
    check_in_time: time
    is_private: bool = False
    time_window: int  # Grace period for challenge post in minutes


class ChallengeCreate(ChallengeBase):
    pass


class ChallengeUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    location: Optional[str] = None
    restriction: Optional[str] = None
    repetition: Optional[str] = Field(None, pattern='^(daily|weekly|monthly|custom|none)$')
    repetition_frequency: Optional[int] = None
    repetition_days: Optional[List[int]] = None
    check_in_time: Optional[time] = None
    is_private: Optional[bool] = None
    time_window: Optional[int] = None


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
    success_count: Optional[int] = None


class ChallengeAchievement(BaseModel):
    id: UUID
    challenge_id: UUID
    user_id: UUID
    achievement_type: str = Field(..., pattern='^(success_rate|completion)$')
    description: str
    achieved_at: datetime
    success_count: Optional[int] = None

    class Config:
        from_attributes = True 