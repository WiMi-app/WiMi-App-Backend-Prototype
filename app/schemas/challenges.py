from datetime import datetime, time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, HttpUrl

from app.schemas.users import User
from app.schemas.posts import Post

'''CHALLENGES'''
class ChallengeBase(BaseModel):
    title: str
    description: str
    due_date: Optional[datetime] = None
    location: Optional[str] = None
    restriction: Optional[str] = None
    repetition: str = None  # 'daily', 'weekly', 'monthly', 'custom'
    repetition_frequency: Optional[int] = None  # e.g., 3 for "every 3 days"
    repetition_days: Optional[List[int]] = None  # For weekly challenges: [1,3,5] for Mon,Wed,Fri
    check_in_time: time
    is_private: bool = False
    time_window: int



class ChallengeCreate(ChallengeBase):
    pass


class ChallengeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    location: Optional[str] = None
    restriction: Optional[str] = None
    repetition: Optional[str] = None
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
    status: str = "active"  # 'active', 'completed', 'dropped'

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
    achievement_type: str  # 'success rate', 'completion'
    description: str
    success_count: Optional[int] = None


class ChallengeAchievement(BaseModel):
    id: UUID
    challenge_id: UUID
    user_id: UUID
    achievement_type: str
    description: str
    achieved_at: datetime
    success_count: Optional[int] = None

    class Config:
        from_attributes = True 