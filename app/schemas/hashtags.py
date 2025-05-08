from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class HashtagOut(BaseModel):
    id: str
    tag: str = Field(..., min_length=1, max_length=50)
    usage_count: int = Field(..., ge=0)
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
