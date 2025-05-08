import sys
import os
from datetime import datetime
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from gotrue.errors import AuthApiError

from app.core.config import supabase
from app.core.security import verify_password, hash_password
from app.schemas.auth import UserSignUp, Token
from app.schemas.users import UserOut

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(user: UserSignUp):
    # Generate a username from email (before @ symbol)
    username = user.email.split('@')[0]
    
    # Hash password and create user in Auth and 'users' table
    hashed = hash_password(user.password)
    try:
        # Create auth user in Supabase
        logger.info(f"Creating auth user for email: {user.email}")
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": hashed
        })
        
        # Extract user ID from auth response
        if not auth_response.user:
            logger.error("Auth response missing user object")
            raise HTTPException(status_code=400, detail="Failed to create user account")
            
        user_id = auth_response.user.id
        logger.info(f"User created with ID: {user_id}")
        
        # Current timestamp
        now = datetime.now()
        
        # Prepare profile data matching DB schema
        profile = {
            "id": user_id,
            "username": username,
            "full_name": "",
            "bio": None,
            "avatar_url": None,
            "updated_at": now
        }
        
        # Insert into users table
        logger.info(f"Inserting user profile into database: {profile}")
        result = supabase.table("users").insert(profile).execute()
        
        # Return user data
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
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        auth_resp = supabase.auth.sign_in_with_password({
            "email": form_data.username, 
            "password": form_data.password
        })
        
        # Validate session
        if not getattr(auth_resp, "session", None):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        access_token = auth_resp.session.access_token
        return Token(access_token=access_token, token_type="bearer")
    except AuthApiError as e:
        logger.error(f"Auth error during login: {str(e)}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    except Exception as e:
        logger.error(f"Unexpected error in login: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")