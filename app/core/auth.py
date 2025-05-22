import time

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError

from app.core.config import settings

security = HTTPBearer()

def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify the JWT token from Supabase.
    
    Args:
        credentials: The HTTP Authorization credentials
        
    Returns:
        dict: The decoded JWT payload
        
    Raises:
        HTTPException: If the token is invalid or expired
    """
    try:
        # Get the JWT token from the Authorization header
        token = credentials.credentials
        
        # Decode and verify the token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,  # This should be your Supabase JWT secret
            algorithms=["HS256"]
        )
        
        # Check if token is expired
        if payload.get("exp") and payload.get("exp") < time.time():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Dependency for requiring authentication
require_auth = Depends(verify_jwt)

# Get the current user's ID from the JWT
def get_current_user_id(payload=Depends(verify_jwt)) -> str:
    """
    Extract the user ID from a verified JWT token.
    
    Args:
        payload: The decoded JWT payload
        
    Returns:
        str: The user ID
        
    Raises:
        HTTPException: If user ID is not found in the token
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token",
        )
    return user_id 