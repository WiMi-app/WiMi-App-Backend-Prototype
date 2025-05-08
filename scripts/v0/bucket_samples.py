import os
import requests
from supabase import create_client, Client

# Configuration: Picsum photo IDs for avatars and post media
AVATAR_IDS = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
MEDIA_IDS = [200, 201, 202, 203, 204, 205, 206, 207]
AVATAR_BUCKET = 'avatars'
MEDIA_BUCKET = 'post_media'

# Initialize Supabase client
def init_supabase() -> Client:
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        raise ValueError('SUPABASE_URL and SUPABASE_KEY must be set as environment variables')
    return create_client(url, key)

# Ensure bucket exists (create if not)
def ensure_bucket(supabase: Client, bucket_name: str):
    try:
        supabase.storage.create_bucket(bucket_name)
        print(f"Created bucket '{bucket_name}'")
    except Exception as e:
        # Ignore if already exists
        if 'already exists' in str(e).lower():
            print(f"Bucket '{bucket_name}' already exists")
        else:
            print(f"Error creating bucket '{bucket_name}': {e}")

# Fetch image bytes from Picsum
def fetch_image(width: int = 500, height: int = 500) -> bytes:
    url = f'https://picsum.photos/{width}/{height}'
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.content

# Upload bytes to Supabase bucket
def upload_image(supabase: Client, bucket: str, path: str, data: bytes):
    try:
        supabase.storage.from_(bucket).upload(path, data)
        print(f"Uploaded to {bucket}/{path}")
    except Exception as e:
        print(f"Failed to upload {path} to bucket '{bucket}': {e}")

# Main function
def main():
    supabase = init_supabase()

    try:
        ensure_bucket(supabase, AVATAR_BUCKET)
    except Exception as e:
        print(f"Error creating buckets: {e}")   

    try:
        ensure_bucket(supabase, MEDIA_BUCKET)
    except Exception as e:
        print(f"Error creating buckets: {e}")
    
    # Upload avatars
    for idx, photo_id in enumerate(AVATAR_IDS, start=1):
        image_bytes = fetch_image(256, 256)
        filename = f'user_{idx}.jpg'
        upload_image(supabase, AVATAR_BUCKET, filename, image_bytes)

    # Upload post media
    for idx, photo_id in enumerate(MEDIA_IDS, start=1):
        image_bytes = fetch_image(800, 800)
        filename = f'media_{idx}.jpg'
        upload_image(supabase, MEDIA_BUCKET, filename, image_bytes)

if __name__ == '__main__':
    main()
