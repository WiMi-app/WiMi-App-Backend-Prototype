from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserSignUp(BaseModel):
    """
    Schema for user registration data.
    """
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ..., min_length=8, description="Password (at least 8 characters)"
    )

class UserLogin(BaseModel):
    """
    Schema for user login data.
    """
    email: EmailStr = Field(..., description="Registered email")
    password: str = Field(
        ..., min_length=8, description="User password"
    )

class Token(BaseModel):
    """
    Schema for auth token response.
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    model_config = ConfigDict(from_attributes=True)

# Schema for refresh token requests
class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")
