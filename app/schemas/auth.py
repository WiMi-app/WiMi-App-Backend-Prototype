from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class TokenData(BaseModel):
    access_token: str
    token_type: str
    user_id: UUID
    expires: datetime


class TokenPayload(BaseModel):
    sub: Optional[UUID] = None
    exp: Optional[float] = None  # Using float for timestamp
    
    @field_validator('exp')
    def validate_exp(cls, v):
        # Handle both timestamp and datetime formats
        if isinstance(v, datetime):
            return v.timestamp()
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SearchResults(BaseModel):
    users: List = []
    posts: List = []
    hashtags: List = [] 