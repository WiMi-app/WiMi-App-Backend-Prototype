from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class NotificationBase(BaseModel):
    user_id: UUID
    triggered_by_user_id: Optional[UUID] = None
    post_id: Optional[UUID] = None
    comment_id: Optional[UUID] = None
    type: str
    message: str
    is_read: bool = False


class NotificationCreate(NotificationBase):
    pass


class Notification(NotificationBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True 