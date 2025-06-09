"""
Media handling utilities for Supabase Storage.

This module contains functions for uploading, retrieving, and managing media files
in Supabase Storage buckets.
"""
import base64
import io
import logging
import os
import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import HTTPException, UploadFile, status

from app.core.config import supabase

logger = logging.getLogger(__name__)

# Define the bucket types
BucketType = Literal["profiles", "post_media", "endorsements"]

# Map of bucket names
BUCKETS = {
    "profiles": "profiles",
    "post_media": "post_media", 
    "endorsements": "endorsements"
}

async def upload_base64_image(
    bucket: BucketType,
    base64_data: str,
    user_id: str,
    content_type: str = "image/jpeg,image/png,image/jpg,image/webp,image/heic,image/heif",
    folder: Optional[str] = None
) -> str:
    """
    Upload a base64 encoded image to a Supabase Storage bucket.
    
    Args:
        bucket: The bucket type to upload to
        base64_data: Base64 encoded image data
        user_id: User ID for file path organization
        content_type: MIME type of the image
        folder: Optional subfolder within the bucket
        
    Returns:
        str: The public URL of the uploaded file
        
    Raises:
        HTTPException: If upload fails
    """
    try:
        # Strip data URI prefix if present
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(base64_data)
        
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uuid.uuid4().hex}.jpg"
        
        # Create path with user_id for organization
        path = f"{user_id}/{filename}"
        if folder:
            path = f"{folder}/{path}"
            
        # Upload to Supabase Storage
        result = supabase.storage.from_(BUCKETS[bucket]).upload(
            path=path,
            file=image_bytes,
            file_options={"content-type": content_type}
        )
        
        # Get the public URL
        file_path = result.path

        if not file_path:
            raise ValueError("Upload succeeded but path not returned")
            
        public_url = supabase.storage.from_(BUCKETS[bucket]).get_public_url(file_path)
        logger.info(f"Successfully uploaded file to {bucket}/{path}")
        
        return public_url
    except Exception as e:
        logger.error(f"Failed to upload image to {bucket}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )

async def upload_file(
    bucket: BucketType,
    file: UploadFile,
    user_id: str,
    folder: Optional[str] = None
) -> str:
    """
    Upload a file to a Supabase Storage bucket.
    
    Args:
        bucket: The bucket type to upload to
        file: FastAPI UploadFile object
        user_id: User ID for file path organization
        folder: Optional subfolder within the bucket
        
    Returns:
        str: The public URL of the uploaded file
        
    Raises:
        HTTPException: If upload fails
    """
    try:
        # Read file content
        contents = await file.read()
        
        # Get file extension
        _, ext = os.path.splitext(file.filename)
        if not ext:
            # Default to .jpg for images without extension
            ext = ".jpg"
            
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uuid.uuid4().hex}{ext}"
        
        # Create path with user_id for organization
        path = f"{user_id}/{filename}"
        if folder:
            path = f"{folder}/{path}"
            
        # Upload to Supabase Storage
        result = supabase.storage.from_(BUCKETS[bucket]).upload(
            path=path,
            file=contents,
            file_options={"content-type": file.content_type}
        )
        
        # Get the public URL
        file_path = result.get("path")
        if not file_path:
            raise ValueError("Upload succeeded but path not returned")
            
        public_url = supabase.storage.from_(BUCKETS[bucket]).get_public_url(file_path)
        logger.info(f"Successfully uploaded file to {bucket}/{path}")
        
        return public_url
    except Exception as e:
        logger.error(f"Failed to upload file to {bucket}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

def delete_file(bucket: BucketType, file_path: str) -> bool:
    """
    Delete a file from a Supabase Storage bucket.
    
    Args:
        bucket: The bucket type
        file_path: Path of the file to delete
        
    Returns:
        bool: True if deletion was successful
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        # Extract the path from a full URL if needed
        if file_path.startswith("http"):
            parts = file_path.split(f"{BUCKETS[bucket]}/")
            if len(parts) > 1:
                file_path = parts[1]
        
        # Delete the file
        supabase.storage.from_(BUCKETS[bucket]).remove([file_path])
        logger.info(f"Successfully deleted file from {bucket}/{file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete file from {bucket}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )

def get_media_url(bucket: BucketType, path: str) -> str:
    """
    Get the public URL for a file in a storage bucket.
    
    Args:
        bucket: The bucket type
        path: Path of the file
        
    Returns:
        str: The public URL of the file
    """
    return supabase.storage.from_(BUCKETS[bucket]).get_public_url(path) 