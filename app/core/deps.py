import urllib.parse

import requests
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
    auth_header = None
    
    # Try to get token from Authorization header
    if credentials:
        auth_header = f"Bearer {credentials.credentials}"
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
            
        auth_header = f"Bearer {token}"
        
    if not auth_header:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    
    # Validate token against Supabase GoTrue
    url = f"{settings.SUPABASE_URL}/auth/v1/user"
    headers = {"apikey": settings.SUPABASE_KEY, "Authorization": auth_header}
    user_resp = requests.get(url, headers=headers)
    if user_resp.status_code != 200:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    user_data = user_resp.json()

    # Fetch user profile from database
    resp = supabase.table("users")\
        .select("id,username,email,full_name,avatar_url,bio,updated_at")\
        .eq("id", user_data["id"])\
        .single().execute()
    if not resp.data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return UserOut(**resp.data)
