from pydantic import BaseModel, EmailStr, Field

class UserSignUp(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ..., min_length=8, description="Password (at least 8 characters)"
    )

class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Registered email")
    password: str = Field(
        ..., min_length=8, description="User password"
    )

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

    class Config:
        orm_mode = True
