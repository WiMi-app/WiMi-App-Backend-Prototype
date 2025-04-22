"""
Dependencies for FastAPI endpoints.
Includes authentication, database connections, and other shared dependencies.
"""
from datetime import datetime, timezone
from typing import Generator, Optional, Dict, Any
from uuid import UUID

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
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
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
        
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        # Check if token has expired
        if token_data.exp is None:
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
    
    # Get user from Supabase
    supabase = get_supabase()
    response = (
        supabase.table("users")
        .select("id, email, is_active, is_admin, created_at")
        .eq("id", token_data.sub)
        .single()
        .execute()
    )
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user = response.data
    
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
        
    return user


def get_current_active_user(current_user: Dict = Depends(get_current_user)) -> Dict:
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


def get_current_admin_user(current_user: Dict = Depends(get_current_user)) -> Dict:
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
    supabase = get_supabase()
    
    try:
        # Get user by email
        response = (
            supabase.table("users")
            .select("id, email, password, is_active, is_admin")
            .eq("email", email)
            .single()
            .execute()
        )
        
        if not response.data:
            return None
            
        user = response.data
        
        # Verify password
        if not verify_password(password, user.get("password", "")):
            return None
            
        # Check if user is active
        if not user.get("is_active", False):
            return None
            
        return user
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return None


def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    db: Client = Depends(get_supabase),
) -> User:
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
    
    user_data = db.table("users").select("*").eq("id", user_id).execute()
    
    if user_data.data is None or len(user_data.data) == 0:
        raise HTTPException(status_code=404, detail="User not found")
        
    return User(**user_data.data[0])


async def check_if_admin(current_user: User = Depends(get_current_user_from_token)) -> bool:
    """
    Checks if the current user has admin role.
    Returns True if user is admin, otherwise False.
    """

    return current_user.role == "admin" if hasattr(current_user, "role") else False 