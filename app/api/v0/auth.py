from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from supabase import Client
import logging
import httpx
from app.core.config import settings
from app.core.deps import authenticate_user, get_current_user
from app.core.security import create_access_token, get_password_hash
from app.db.database import get_supabase
from app.schemas.auth import TokenData, LoginRequest
from app.schemas.users import User, UserCreate
logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/login", response_model=TokenData)
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Client = Depends(get_supabase),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    You can use either email or username for authentication.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    
    # Update last login time
    now = datetime.now(timezone.utc).isoformat()
    db.table("users").update({"last_login": now}).eq("id", str(user.id)).execute()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "expires": datetime.now(timezone.utc) + access_token_expires,
    }


@router.post("/login/email", response_model=TokenData)
def login_email(
    login_data: LoginRequest,
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Login with email and password, get an access token for future requests.
    """
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    
    # Update last login time
    now = datetime.now(timezone.utc).isoformat()
    db.table("users").update({"last_login": now}).eq("id", str(user.id)).execute()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "expires": datetime.now(timezone.utc) + access_token_expires,
    }



@router.post("/register", response_model=User)
def register_user(
    user_data: UserCreate,
    db: Client = Depends(get_supabase),
) -> Any:
    """
    Register a new user.
    """
    # Check if email already exists
    existing_user = db.table("users").select("*").eq("email", user_data.email).execute()
    if existing_user.data and len(existing_user.data) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Check if username already exists
    existing_username = db.table("users").select("*").eq("username", user_data.username).execute()
    if existing_username.data and len(existing_username.data) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    
    # Hash the password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user dict for insertion using the safe method
    now = datetime.now(timezone.utc).isoformat()
    user_dict = user_data.model_dump_json_safe()
    
    user_dict.update({
        "password_hash": hashed_password,
        "created_at": now,
        "updated_at": now,
    })
    
    # Insert user into database
    result = db.table("users").insert(user_dict).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )
    
    return User(**result.data[0])


@router.get("/verify-token", response_model=Dict[str, Any])
def verify_token(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Debug endpoint to verify if a token is valid.
    Returns user information if the token is valid.
    """
    logger.info(f"Token verification successful for user: {current_user.id}")
    return {
        "status": "success",
        "message": "Token is valid",
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    } 