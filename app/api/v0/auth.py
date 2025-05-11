import json
import logging
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from gotrue.errors import AuthApiError

from app.core.config import supabase
from app.core.security import hash_password, verify_password
from app.schemas.auth import Token, UserSignUp
from app.schemas.users import UserOut

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(user: UserSignUp):
    # Generate a username from email (before @ symbol)
    username = user.email.split('@')[0]
    
    # Create user in Auth and 'users' table
    try:
        # Create auth user in Supabase
        logger.info(f"Creating auth user for email: {user.email}")
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password  # Supabase handles hashing
        })
        
        # Extract user ID from auth response
        if not auth_response.user:
            logger.error("Auth response missing user object")
            raise HTTPException(status_code=400, detail="Failed to create user account")
            
        user_id = auth_response.user.id
        logger.info(f"User created with ID: {user_id}")
        
        # Current timestamp
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        
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
    """
    OAuth2 compatible token login, using either email or username.
    
    If an email is provided, it will be used directly for authentication.
    If a username is provided, we'll look up the corresponding email first.
    """
    try:
        # Check if the input looks like an email (contains @)
        login_id = form_data.username
        
        if '@' not in login_id:
            # This looks like a username, not an email
            logger.info(f"Username login attempt: {login_id}")
            
            # Look up the user by username to find their email
            user_result = supabase.table("users").select("id").eq("username", login_id).execute()
            
            if not user_result.data or len(user_result.data) == 0:
                logger.error(f"No user found with username: {login_id}")
                raise HTTPException(status_code=401, detail="Incorrect username or password")
            
            # Get the user ID
            user_id = user_result.data[0]["id"]
            logger.info(f"Found user ID for username {login_id}: {user_id}")
            
            # Get the email for this user ID from auth.users (only service role can do this)
            # We need to use the admin API for this
            try:
                auth_user = supabase.auth.admin.get_user_by_id(user_id)
                if not auth_user or not auth_user.user:
                    logger.error(f"Failed to find auth user for ID: {user_id}")
                    raise HTTPException(status_code=401, detail="Invalid user credentials")
                
                email = auth_user.user.email
                if not email:
                    logger.error(f"Auth user has no email: {user_id}")
                    raise HTTPException(status_code=401, detail="Invalid user account")
                
                logger.info(f"Found email for username {login_id}: {email}")
            except Exception as e:
                logger.error(f"Error fetching user email: {str(e)}")
                raise HTTPException(status_code=401, detail="Invalid user credentials")
        else:
            # This looks like an email, use it directly
            email = login_id
            logger.info(f"Email login attempt: {email}")
        
        # Sign in with Supabase using email and password
        auth_resp = supabase.auth.sign_in_with_password({
            "email": email, 
            "password": form_data.password
        })
        
        # Validate session
        if not getattr(auth_resp, "session", None):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        access_token = auth_resp.session.access_token
        return Token(access_token=access_token, token_type="bearer")
    except AuthApiError as e:
        logger.error(f"Supabase auth error: {str(e)}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    except HTTPException:
        raise # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Unexpected error in login: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")