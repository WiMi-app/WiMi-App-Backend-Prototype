from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class MessageBase(BaseModel):
    content: str
    media_url: Optional[HttpUrl] = None


class MessageCreate(MessageBase):
    recipient_id: UUID


class Message(MessageBase):
    id: UUID
    sender_id: UUID
    recipient_id: UUID
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True 