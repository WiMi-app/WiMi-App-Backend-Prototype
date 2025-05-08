from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from app.core.config import settings
from app.core.security import decode_access_token
from app.schemas.users import UserOut

auth_scheme = HTTPBearer(auto_error=False)

def get_supabase() -> Client:
    from core.config import supabase  # your Supabase client init
    return supabase

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(auth_scheme),
    supabase: Client = Depends(get_supabase),
) -> UserOut:
    if not creds or not creds.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        user_id = decode_access_token(creds.credentials)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    resp = supabase.from_("users").select("*").eq("id", user_id).single()
    if resp.error or not resp.data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return UserOut(**resp.data)
