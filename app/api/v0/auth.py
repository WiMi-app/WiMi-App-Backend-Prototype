import json
import logging
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from fastapi import APIRouter, HTTPException, Response, status
from gotrue.errors import AuthApiError

from app.core.config import settings, supabase
from app.schemas.auth import RefreshTokenRequest, Token, UserLogin, UserSignUp
from app.schemas.users import UserOut

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(user: UserSignUp):
    """
    Register a new user with email and password.
    
    Args:
        user (UserSignUp): User registration data containing email and password
    
    Returns:
        UserOut: Newly created user data
        
    Raises:
        HTTPException: 400 if registration fails
        HTTPException: 500 if unexpected error occurs
    """
    username = user.email.split('@')[0]
    
    try:
        logger.info(f"Creating auth user for email: {user.email}")
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
        
        if not auth_response.user:
            logger.error("Auth response missing user object")
            raise HTTPException(status_code=400, detail="Failed to create user account")
            
        user_id = auth_response.user.id
        logger.info(f"User created with ID: {user_id}")
        
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        
        profile = {
            "id": user_id,
            "username": username,
            "full_name": "",
            "email": user.email,
            "bio": None,
            "avatar_url": None,
            "updated_at": now
        }
        
        logger.info(f"Inserting user profile into database: {profile}")
        result = supabase.table("users").insert(profile).execute()
        
        return UserOut(
            id=user_id,
            email=user.email,
            username=username,
            full_name="",
            avatar_url=None,
            bio=None,
            updated_at=now
        )
    except AuthApiError as e:
        logger.error(f"Supabase auth error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in signup: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@router.post("/token", response_model=Token)
async def login_for_access_token(user_login: UserLogin, response: Response):
    """
    Token login using email and password via JSON.
    """
    try:
        email = user_login.email
        password = user_login.password
        logger.info(f"Login attempt for email: {email}")
        auth_resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
        
        if not getattr(auth_resp, "session", None):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        access_token = auth_resp.session.access_token
        refresh_token = auth_resp.session.refresh_token
        
        # set JWT in cookie for browser-based auth
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )
        
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")
   
    except AuthApiError as e:
        logger.error(f"Supabase auth error: {str(e)}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in login: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    """
    Logs out the user (token-based, no cookies to delete).
    """
    # Remove the stored JWT cookie so the user is fully logged out
    response.delete_cookie(key="access_token", path="/")
    return {"detail": "Successfully logged out"}

@router.post("/refresh", response_model=Token)
async def refresh_access_token(request: RefreshTokenRequest):
    """
    Refresh the tokens using the provided refresh token.
    
    Args:
        request (RefreshTokenRequest): JSON body with refresh_token
    
    Returns:
        Token: New access token and refresh token
        
    """
    if not request.refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    
    try:
        # Use Supabase SDK to refresh the token
        auth_response = supabase.auth.refresh_session(request.refresh_token)
        
        if not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to refresh token"
            )
        
        access_token = auth_response.session.access_token
        new_refresh_token = auth_response.session.refresh_token
        token_type = auth_response.session.token_type
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type=token_type
        )
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )