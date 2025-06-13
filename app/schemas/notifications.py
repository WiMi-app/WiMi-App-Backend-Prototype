from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator


class NotificationType(str, Enum):
    """
    Enumeration of supported notification types.
    """
    LIKE = "like"
    COMMENT = "comment"
    FOLLOW = "follow"
    MENTION = "mention"
    ENDORSEMENT_REQUEST = "endorsement_request"
    POST_ENDORSED = "post_endorsed"
    
class NotificationStatus(str, Enum):
    """
    Enumeration of supported notification statuses.
    """
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"

class NotificationOut(BaseModel):
    """
    Schema for notification data returned by the API.
    Includes all notification fields including type classification.
    """
    id: str
    type: NotificationType
    user_id: str
    triggered_by_id: str
    post_id: str | None = None
    comment_id: str | None = None
    message: str
    is_read: bool
    created_at: datetime
    status: NotificationStatus
    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v