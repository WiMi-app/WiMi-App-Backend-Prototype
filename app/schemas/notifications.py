from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class NotificationType(str, Enum):
    """
    Enumeration of supported notification types.
    """
    LIKE = "like"
    COMMENT = "comment"
    FOLLOW = "follow"
    MENTION = "mention"

class NotificationOut(BaseModel):
    """
    Schema for notification data returned by the API.
    Includes all notification fields including type classification.
    """
    id: str
    type: NotificationType
    actor_id: str
    recipient_id: str
    target_id: str   # e.g. post/comment ID
    is_read: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
