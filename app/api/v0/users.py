import logging
from datetime import datetime
from typing import Optional

from fastapi import (APIRouter, Cookie, Depends, File, Form, Header,
                     HTTPException, UploadFile, status)
from fastapi.responses import JSONResponse

from app.core.config import supabase
from app.core.deps import get_current_user
from app.core.media import delete_file, upload_base64_image, upload_file
from app.schemas.users import UserOut, UserUpdate

router = APIRouter(tags=["users"])
logger = logging.getLogger(__name__)

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

@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """
    Upload a new avatar image for the current user.
    
    Args:
        file: The image file to upload
        user: Current user from token validation dependency
        
    Returns:
        UserOut: Updated user profile with new avatar URL
    """
    # Check if user has an existing avatar to delete
    if user.avatar_url:
        try:
            delete_file("avatars", user.avatar_url)
        except Exception as e:
            logger.warning(f"Failed to delete old avatar for user {user.id}: {str(e)}")
    
    # Upload the new avatar
    avatar_url = await upload_file("avatars", file, user.id)
    
    # Update the user's avatar_url in the database
    updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    supabase.table("users").update({
        "avatar_url": avatar_url,
        "updated_at": updated_at
    }).eq("id", user.id).execute()
    
    # Return the updated user data
    return supabase.table("users")\
        .select("id,username,full_name,avatar_url,email,bio,updated_at")\
        .eq("id", user.id)\
        .single().execute().data

@router.post("/me/avatar/base64", response_model=UserOut)
async def upload_avatar_base64(
    base64_image: str = Form(...),
    user=Depends(get_current_user)
):
    """
    Upload a new avatar image for the current user using base64 encoded data.
    
    Args:
        base64_image: Base64 encoded image data
        user: Current user from token validation dependency
        
    Returns:
        UserOut: Updated user profile with new avatar URL
    """
    # Check if user has an existing avatar to delete
    if user.avatar_url:
        try:
            delete_file("avatars", user.avatar_url)
        except Exception as e:
            logger.warning(f"Failed to delete old avatar for user {user.id}: {str(e)}")
    
    # Upload the new avatar
    avatar_url = await upload_base64_image("avatars", base64_image, user.id)
    
    # Update the user's avatar_url in the database
    updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    supabase.table("users").update({
        "avatar_url": avatar_url,
        "updated_at": updated_at
    }).eq("id", user.id).execute()
    
    # Return the updated user data
    return supabase.table("users")\
        .select("id,username,full_name,avatar_url,email,bio,updated_at")\
        .eq("id", user.id)\
        .single().execute().data

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, current_user=Depends(get_current_user)):
    """
    Delete a user completely from the system including auth.users and public.users tables.
    
    This is an admin-level operation and requires a service_role key.
    The user's data will be completely removed from the system.
    
    Args:
        user_id (str): UUID of the user to delete
        current_user: Current authenticated user (for authorization)
        
    Returns:
        None: 204 No Content response
        
    Raises:
        HTTPException: 403 if not authorized
        HTTPException: 404 if user not found
        HTTPException: 500 if deletion fails
    """
    try:
        # Only allow admins to delete users
        # In a real system you would have proper admin checks
        # This is a simplified check - in practice, implement proper RBAC
        if current_user.id != user_id:
            logger.warning(f"Unauthorized delete attempt: {current_user.id} tried to delete {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Not authorized to delete other users"
            )
            
        # Check if user exists in public.users table
        user = supabase.table("users").select("id,avatar_url").eq("id", user_id).single().execute()
        
        if not user.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # Delete avatar if it exists
        if user.data.get("avatar_url"):
            try:
                delete_file("avatars", user.data["avatar_url"])
            except Exception as e:
                logger.warning(f"Failed to delete avatar for user {user_id}: {str(e)}")

        # Delete from public.users first
        logger.info(f"Deleting user {user_id} from public.users table")
        supabase.table("users").delete().eq("id", user_id).execute()
        
        # Delete from auth.users using the admin API
        logger.info(f"Deleting user {user_id} from auth.users table")
        supabase.auth.admin.delete_user(user_id)
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )
        
