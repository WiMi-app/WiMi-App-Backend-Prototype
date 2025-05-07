"""
Dependencies for FastAPI endpoints.
Includes authentication, database connections, and other shared dependencies.
"""
from datetime import datetime, timezone
from typing import Generator, Optional, Dict, Any, Union, List
from uuid import UUID
import os

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError, ExpiredSignatureError
from pydantic import ValidationError
from supabase import Client
import logging

from app.core.config import settings
from app.core.security import verify_password
from app.db.database import get_supabase
from app.schemas.auth import TokenPayload
from app.schemas.users import User

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"/api/v0/auth/login",
    auto_error=False  # Don't auto-raise errors for optional auth
)


def get_current_user(token: str = Depends(oauth2_scheme)) -> Optional[Dict[str, Any]]:
    """
    Validate access token and return current user data.
    
    Args:
        token: JWT token from request
        
    Returns:
        Optional[Dict[str, Any]]: User data if authenticated, None otherwise
        
    Raises:
        HTTPException: If token invalid or user not found
    """
    if not token:
        return None
        
    # For development, allow mock authentication if enabled
    if settings.ENVIRONMENT == "development" and settings.MOCK_AUTH and token == "development_token":
        logger.debug("Using mock authentication token")
        return {
            "id": "00000000-0000-0000-0000-000000000000",
            "email": "dev@example.com",
            "is_active": True,
            "is_admin": True,
            "display_name": "Development User",
            "phone": "+15555555555",
            "providers": ["email"],
            "provider_type": "email",
            "last_sign_in_at": datetime.now(timezone.utc).isoformat()
        }
        
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        # Check if token has expired
        if token_data.exp is None:
            logger.warning("Token has no expiration")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has no expiration",
            )
            
    except (JWTError, ValidationError) as e:
        logger.warning(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    try:
        # Get user from Supabase
        supabase = get_supabase()
        
        # First check auth.users table to get authentication information
        auth_user_response = None
        try:
            # Note: In production with Supabase, you would use the auth.users table via RPC calls
            # or admin API since direct access is restricted
            auth_user_response = (
                supabase.rpc(
                    "get_auth_user_by_id", 
                    {"user_id": token_data.sub}
                ).execute()
            )
        except Exception as e:
            if settings.ENVIRONMENT == "development":
                logger.warning(f"Could not fetch auth user data: {str(e)}")
        
        # Then get the user profile data from the public users table
        response = (
            supabase.table("users")
            .select("id, username, full_name, avatar_url, bio, updated_at")
            .eq("id", token_data.sub)
            .single()
            .execute()
        )
        
        if not response.data:
            if settings.ENVIRONMENT == "development":
                # In development, provide detailed error
                logger.warning(f"User not found: {token_data.sub}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        user = response.data
        
        # Merge auth data if available
        if auth_user_response and auth_user_response.data:
            auth_data = auth_user_response.data
            # Map Supabase auth fields to our custom fields
            auth_fields = {
                "email": auth_data.get("email"),
                "phone": auth_data.get("phone"),
                "display_name": auth_data.get("display_name", user.get("full_name")),
                "providers": auth_data.get("providers", []),
                "provider_type": auth_data.get("provider_type"),
                "created_at": auth_data.get("created_at"),
                "last_sign_in_at": auth_data.get("last_sign_in_at")
            }
            user.update(auth_fields)
        elif settings.ENVIRONMENT == "development":
            # In development: mock auth data when auth API is not accessible
            mock_auth_fields = {
                "email": f"{user.get('username')}@example.com",
                "phone": None,
                "display_name": user.get("full_name"),
                "providers": ["email"],
                "provider_type": "email",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_sign_in_at": datetime.now(timezone.utc).isoformat()
            }
            user.update(mock_auth_fields)
            
        # Check if user is active - in Supabase this would be handled by auth.users
        if user.get("is_active") is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )
            
        return user
    except Exception as e:
        if settings.ENVIRONMENT == "development":
            # In development, provide more helpful error messages
            logger.error(f"Error fetching user data: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching user data: {str(e)}",
            )
        else:
            # In production, don't expose detailed errors
            logger.error(f"Database error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )


def get_current_active_user(current_user: Optional[Dict] = Depends(get_current_user)) -> Dict:
    """
    Get current user with verification that user is active.
    
    Args:
        current_user: User data from token validation
        
    Returns:
        Dict: Active user data
        
    Raises:
        HTTPException: If no user or user inactive
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
        
    return current_user


def get_current_admin_user(current_user: Optional[Dict] = Depends(get_current_user)) -> Dict:
    """
    Get current user with verification that user is an admin.
    
    Args:
        current_user: User data from token validation
        
    Returns:
        Dict: Admin user data
        
    Raises:
        HTTPException: If user not admin
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
        
    if not current_user.get("is_admin", False):
        # For development, provide a way to bypass admin check with config
        if settings.ENVIRONMENT == "development" and os.getenv("BYPASS_ADMIN_CHECK", "").lower() == "true":
            logger.warning(f"Bypassing admin check for user {current_user.get('id')} in development")
            return current_user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
        
    return current_user


def authenticate_user(email: str, password: str) -> Optional[Dict]:
    """
    Authenticate a user by email and password.
    
    Args:
        email: User's email
        password: User's password
        
    Returns:
        Optional[Dict]: User data if authentication successful, None otherwise
    """
    # In development mode with mock auth, allow test credentials
    if settings.ENVIRONMENT == "development" and settings.MOCK_AUTH:
        if email == "dev@example.com" and password == "password":
            logger.debug("Using mock authentication credentials")
            return {
                "id": "00000000-0000-0000-0000-000000000000",
                "email": "dev@example.com",
                "password": "hashed_password",
                "is_active": True,
                "is_admin": True,
                "display_name": "Development User",
                "phone": None,
                "providers": ["email"],
                "provider_type": "email",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_sign_in_at": datetime.now(timezone.utc).isoformat()
            }
    
    try:
        # In production, this would be handled by Supabase Authentication
        # Here we're simulating the behavior for development
        supabase = get_supabase()
        
        # First, check if this is an email login
        user_response = None
        try:
            user_response = (
                supabase.table("users")
                .select("id, username, full_name")
                .eq("email", email)
                .single()
                .execute()
            )
        except Exception as e:
            if settings.ENVIRONMENT == "development":
                logger.warning(f"Error fetching user by email: {str(e)}")
                
        # If no user found by email, check auth system
        if not user_response or not user_response.data:
            try:
                # Note: In production with Supabase, you would use their auth system
                auth_response = (
                    supabase.rpc(
                        "get_auth_user_by_email", 
                        {"user_email": email}
                    ).execute()
                )
                
                if auth_response.data:
                    user_id = auth_response.data.get("id")
                    if user_id:
                        user_response = (
                            supabase.table("users")
                            .select("id, username, full_name")
                            .eq("id", user_id)
                            .single()
                            .execute()
                        )
            except Exception as e:
                if settings.ENVIRONMENT == "development":
                    logger.warning(f"Error fetching auth user: {str(e)}")
            
        if not user_response or not user_response.data:
            return None
            
        user = user_response.data
            
        # Verify password - in production this would be handled by Supabase Auth
        # Here we're checking against our own password field for development
        try:
            auth_response = (
                supabase.rpc(
                    "verify_user_password", 
                    {"user_id": user["id"], "password_text": password}
                ).execute()
            )
            
            if not auth_response.data or not auth_response.data.get("valid", False):
                return None
        except Exception as e:
            if settings.ENVIRONMENT == "development":
                logger.warning(f"Error verifying password: {str(e)}")
                # Fall back to direct password check in development
                password_response = (
                    supabase.table("users")
                    .select("password")
                    .eq("id", user["id"])
                    .single()
                    .execute()
                )
                
                if not password_response.data or not verify_password(password, password_response.data.get("password", "")):
                    return None
            else:
                return None
            
        # Get full user details
        full_user_response = (
            supabase.table("users")
            .select("*")
            .eq("id", user["id"])
            .single()
            .execute()
        )
        
        if not full_user_response.data:
            return None
            
        full_user = full_user_response.data
        
        # Add auth-specific fields
        auth_fields = {
            "email": email,
            "is_active": True, 
            "providers": ["email"],
            "provider_type": "email",
            "display_name": full_user.get("full_name"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_sign_in_at": datetime.now(timezone.utc).isoformat()
        }
        full_user.update(auth_fields)
            
        return full_user
        
    except Exception as e:
        if settings.ENVIRONMENT == "development":
            # In development, log detailed error
            logger.error(f"Authentication error: {str(e)}")
        else:
            # In production, log without details
            logger.error("Authentication database error")
        return None


def get_auth_provider_for_user(user_id: str) -> Optional[str]:
    """
    Get the authentication provider for a user.
    
    Args:
        user_id: User ID to check
        
    Returns:
        Optional[str]: Authentication provider ('email', 'phone', 'google', 'apple') or None if not found
    """
    try:
        supabase = get_supabase()
        auth_response = None
        
        try:
            # Try to get auth data from Supabase
            auth_response = supabase.rpc("get_auth_user_by_id", {"user_id": user_id}).execute()
        except Exception as e:
            if settings.ENVIRONMENT == "development":
                logger.warning(f"Could not fetch auth provider: {str(e)}")
                
        if auth_response and auth_response.data:
            provider = auth_response.data.get("provider_type")
            if provider:
                return provider
                
        # Fallback for development or when auth data not accessible
        user_response = (
            supabase.table("users")
            .select("email, phone")
            .eq("id", user_id)
            .single()
            .execute()
        )
        
        if user_response and user_response.data:
            if user_response.data.get("phone"):
                return "phone"
            elif user_response.data.get("email"):
                return "email"
                
        return None
        
    except Exception as e:
        logger.error(f"Error fetching auth provider: {str(e)}")
        return None


def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    db: Client = Depends(get_supabase),
) -> User:
    # For development, allow mock authentication if enabled
    if settings.ENVIRONMENT == "development" and settings.MOCK_AUTH and token == "development_token":
        logger.debug("Using mock user from token")
        # Return a mock user for development
        return User(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            username="dev_user",
            full_name="Development User",
            bio="This is a mock user for development",
            avatar_url="https://example.com/avatar.png",
            updated_at=datetime.now(timezone.utc)
        )
    
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            options={"verify_signature": True}
        )
        token_data = TokenPayload(**payload)
        
        # Use timestamp comparison with UTC for consistency
        current_timestamp = datetime.now(timezone.utc).timestamp()
        if token_data.exp < current_timestamp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id = token_data.sub
    
    try:
        user_data = db.table("users").select("*").eq("id", user_id).execute()
        
        if user_data.data is None or len(user_data.data) == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get the first user object
        user_dict = user_data.data[0]
            
        # Attempt to get auth data to enrich the user object
        try:
            auth_data = db.rpc("get_auth_user_by_id", {"user_id": user_id}).execute()
            if auth_data.data:
                # Only update user dict with non-None values from auth data
                for key, value in auth_data.data.items():
                    if value is not None and key not in user_dict:
                        user_dict[key] = value
                
                # Add created_at from auth since it's not in users table
                if "created_at" not in user_dict and "created_at" in auth_data.data:
                    user_dict["created_at"] = auth_data.data["created_at"]
        except Exception as auth_err:
            if settings.ENVIRONMENT == "development":
                logger.debug(f"Could not fetch auth data: {str(auth_err)}")
                
        return User(**user_dict)
    except Exception as e:
        if settings.ENVIRONMENT == "development":
            # In development, provide more helpful error messages
            logger.error(f"Database error fetching user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error fetching user data",
            )


async def check_if_admin(current_user: User = Depends(get_current_user_from_token)) -> bool:
    """
    Checks if the current user has admin role.
    Returns True if user is admin, otherwise False.
    """
    # For development, enable admin bypass if configured
    if settings.ENVIRONMENT == "development" and os.getenv("BYPASS_ADMIN_CHECK", "").lower() == "true":
        logger.warning(f"Bypassing admin check in development for user {current_user.id}")
        return True

    return current_user.role == "admin" if hasattr(current_user, "role") else False 