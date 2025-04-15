from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class TokenData(BaseModel):
    access_token: str
    token_type: str
    user_id: UUID
    expires: datetime


class TokenPayload(BaseModel):
    sub: Optional[UUID] = None
    exp: Optional[datetime] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SearchResults(BaseModel):
    users: List = []
    posts: List = []
    hashtags: List = [] 