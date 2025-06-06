from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

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
    selfie_url: Optional[List[str]] = Field(None, description="[bucket, filename] of the endorsement selfie image")


class EndorsementOut(BaseModel):
    """
    Schema for endorsement data returned by the API.
    """
    id: str
    post_id: str
    endorser_id: str
    status: EndorsementStatus
    selfie_url: Optional[List[str]] = None
    created_at: datetime
    endorsed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

    @property
    def full_selfie_url(self) -> Optional[str]:
        if self.selfie_url and isinstance(self.selfie_url, list) and len(self.selfie_url) == 2:
            bucket_name, file_name = self.selfie_url
            # Bucket name for selfie_url is "selfie_url"
            return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket_name}//{file_name}"
        return None 