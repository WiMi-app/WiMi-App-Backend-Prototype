from pydantic import BaseModel
from enum import Enum
from datetime import datetime

class NotificationType(str, Enum):
    LIKE = "like"
    COMMENT = "comment"
    FOLLOW = "follow"
    MENTION = "mention"

class NotificationOut(BaseModel):
    id: str
    type: NotificationType
    actor_id: str
    recipient_id: str
    target_id: str   # e.g. post/comment ID
    is_read: bool
    created_at: datetime

    class Config:
        orm_mode = True
