from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EndorsementStatus(str, Enum):
    """
    Enumeration of supported endorsement statuses.
    """
    PENDING = "pending"
    ENDORSED = "endorsed"
    DECLINED = "declined"


class EndorsementBase(BaseModel):
    """
    Base schema for endorsement data.
    Contains common endorsement fields used in multiple schemas.
    """
    post_id: str = Field(..., description="ID of the post to be endorsed")
    endorser_id: str = Field(..., description="ID of the user endorsing the post")
    model_config = ConfigDict(from_attributes=True)


class EndorsementCreate(BaseModel):
    """
    Schema for creating a new endorsement request.
    """
    post_id: str = Field(..., description="ID of the post to be endorsed")
    endorser_id: str = Field(..., description="ID of the user endorsing the post")


class EndorsementUpdate(BaseModel):
    """
    Schema for updating an existing endorsement.
    Used when a user endorses or declines the post.
    """
    status: EndorsementStatus = Field(..., description="New status of the endorsement")
    selfie_url: Optional[str] = Field(None, description="URL of the endorsement selfie image")


class EndorsementOut(BaseModel):
    """
    Schema for endorsement data returned by the API.
    """
    id: str
    post_id: str
    endorser_id: str
    status: EndorsementStatus
    selfie_url: Optional[str] = None
    created_at: datetime
    endorsed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True) 