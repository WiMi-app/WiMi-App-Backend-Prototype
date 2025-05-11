import requests
from fastapi import Depends, HTTPException, status
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
    supabase: Client = Depends(get_supabase),
) -> UserOut:
    """
    Extracts and validates the user from token in multiple possible locations.
    Used as a dependency for protected endpoints.
    
    Args:
        credentials (HTTPAuthorizationCredentials, optional): HTTP Authorization header
        supabase (Client): Supabase client instance
    
    Returns:
        UserOut: Validated user data
        
    Raises:
        HTTPException: 401 if token is missing or invalid
        HTTPException: 401 if user is not found
    """
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    token = credentials.credentials
    
    # Validate token against Supabase GoTrue
    url = f"{settings.SUPABASE_URL}/auth/v1/user"
    headers = {"apikey": settings.SUPABASE_KEY, "Authorization": f"Bearer {token}"}
    user_resp = requests.get(url, headers=headers)
    if user_resp.status_code != 200:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    user_data = user_resp.json()

    # Fetch user profile from database
    resp = supabase.table("users")\
        .select("id,username,email,full_name,avatar_url,bio,updated_at")\
        .eq("id", user_data["id"])\
        .single().execute()
    if resp.error or not resp.data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return UserOut(**resp.data)
