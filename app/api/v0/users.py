from datetime import datetime

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException

from app.core.config import supabase
from app.core.deps import get_current_user
from app.schemas.users import UserOut, UserUpdate

router = APIRouter(tags=["users"])

@router.get(f"/me", response_model=UserOut)
async def read_current_user(user=Depends(get_current_user)):
    """
    Get details of currently authenticated user.
    
    Args:
        user: Current user from token validation dependency
        
    Returns:
        UserOut: User profile data
    """
    return UserOut(**user.__dict__)

@router.get("/{user_id}", response_model=UserOut)
async def read_user(user_id: str):
    """
    Get details of a specific user by ID.
    
    Args:
        user_id (str): UUID of the user to retrieve
        
    Returns:
        UserOut: User profile data
        
    Raises:
        HTTPException: 404 if user not found
    """
    try:
        resp = supabase.table("users")\
            .select("id,username,full_name,avatar_url,email")\
                .eq("id", user_id).single().execute()
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=404, detail="User not found")

@router.get("/by-username/{username}", response_model=UserOut)
async def read_user_by_username(username: str):
    """
    Get details of a specific user by username.
    
    Args:
        username (str): Username of the user to retrieve
        
    Returns:
        UserOut: User profile data
        
    Raises:
        HTTPException: 404 if user not found
    """
    try:
        resp = supabase.table("users")\
            .select("id,username,full_name,avatar_url,email")\
                .eq("username", username).single().execute()
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=404, detail="User not found")

@router.put("/me", response_model=UserOut)
async def update_user(payload: UserUpdate, user=Depends(get_current_user)):
    """
    Update the currently authenticated user's profile data.
    
    Args:
        payload (UserUpdate): Data to update (only provided fields will be updated)
        user: Current user from token validation dependency
        
    Returns:
        UserOut: Updated user profile
    """
    data = payload.model_dump(exclude_unset=True)
    data["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    supabase.table("users").update(data).eq("id", user.id).execute()
    return supabase.table("users")\
        .select("id,username,full_name,avatar_url,email")\
        .eq("id", user.id)\
        .single().execute().data
        
