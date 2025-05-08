import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import supabase
from app.core.security import verify_password, hash_password
from app.schemas.auth import UserSignUp, Token
from app.schemas.users import UserOut

router = APIRouter(prefix="/api/v0/auth", tags=["auth"])

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(user: UserSignUp):
    # Hash password and create user in Auth and 'users' table
    hashed = hash_password(user.password)
    auth_resp = supabase.auth.sign_up({"email": user.email, "password": hashed})
    if auth_resp.error:
        raise HTTPException(status_code=400, detail=auth_resp.error.message)
    # Store additional profile data
    profile = {"id": auth_resp.user.id, "email": user.email, "full_name": None, "avatar_url": None}
    supabase.table("users").insert(profile).execute()
    return UserOut(id=auth_resp.user.id, email=user.email, full_name=None, avatar_url=None)

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    auth_resp = supabase.auth.sign_in_with_password({"email": form_data.username, "password": form_data.password})
    if auth_resp.error or not auth_resp.session:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = auth_resp.session.access_token
    return Token(access_token=access_token, token_type="bearer")