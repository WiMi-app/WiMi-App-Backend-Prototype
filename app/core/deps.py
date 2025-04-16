from datetime import datetime
from typing import Generator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from supabase import Client

from app.core.config import settings
from app.core.security import verify_password
from app.db.database import get_supabase
from app.schemas.auth import TokenPayload
from app.schemas.users import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Client = Depends(get_supabase),
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        if token_data.exp < datetime.utcnow().timestamp():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id = token_data.sub
    
    user_data = db.table("users").select("*").eq("id", user_id).execute()
    
    if user_data.data is None or len(user_data.data) == 0:
        raise HTTPException(status_code=404, detail="User not found")
        
    return User(**user_data.data[0])


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def authenticate_user(db: Client, email_or_username: str, password: str) -> Optional[User]:
    # Try to find user by email first
    user_data = db.table("users").select("*").eq("email", email_or_username).execute()
    
    # If not found by email, try with username
    if user_data.data is None or len(user_data.data) == 0:
        user_data = db.table("users").select("*").eq("username", email_or_username).execute()
    
    if user_data.data is None or len(user_data.data) == 0:
        return None
        
    user = user_data.data[0]
    
    if not verify_password(password, user.get("password_hash")):
        return None
        
    return User(**user) 