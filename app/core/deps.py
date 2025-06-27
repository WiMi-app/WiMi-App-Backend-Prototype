import time
import urllib.parse

import jwt
import requests
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import DecodeError
from supabase import Client

from app.core.config import settings, supabase
from app.schemas.users import UserOut

# HTTP bearer scheme for auth
bearer_scheme = HTTPBearer(auto_error=False)

def get_supabase() -> Client:
    """
    Dependency that provides the Supabase client.
    
    Returns:
        Client: Initialized Supabase client instance
    """
    return supabase

def verify_jwt_token(token: str) -> dict:
    """
    Verify a JWT token from Supabase.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Decoded JWT payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Decode and verify the token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience="authenticated"
        )
        
        # Check if token is expired
        if payload.get("exp") and payload.get("exp") < time.time():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
    except DecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    access_token: str | None = Cookie(None),
    supabase: Client = Depends(get_supabase),
) -> UserOut:
    """
    Extracts and validates the user from token in multiple possible locations.
    Used as a dependency for protected endpoints.
    
    Args:
        credentials (HTTPAuthorizationCredentials, optional): HTTP Authorization header
        access_token (str, optional): Cookie containing access token
        supabase (Client): Supabase client instance
    
    Returns:
        UserOut: Validated user data
        
    Raises:
        HTTPException: 401 if token is missing or invalid
        HTTPException: 401 if user is not found
    """
    token = None
    
    # Try to get token from Authorization header
    if credentials:
        token = credentials.credentials
    # Fall back to cookie if no Authorization header
    elif access_token:
        # Handle URL-encoded tokens and Bearer prefix
        token = access_token
        
        # If token is URL-encoded, decode it
        if '%' in token:
            token = urllib.parse.unquote(token)
            
        # Handle "Bearer " prefix in cookie value
        if token.startswith("Bearer "):
            token = token[7:]  # Remove "Bearer " prefix
        
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    
    # Validate JWT token
    payload = verify_jwt_token(token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User ID not found in token")

    # Fetch user profile from database
    resp = supabase.table("users")\
        .select("id,username,email,full_name,avatar_url,bio,updated_at,fcm_token,timezone")\
        .eq("id", user_id)\
        .single().execute()
    if not resp.data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return UserOut(**resp.data)
