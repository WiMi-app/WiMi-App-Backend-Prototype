"""
Challenges API endpoints for managing challenge resources.
Provides CRUD operations for challenges with authorization controls.
"""
from datetime import datetime, timedelta, time, date
from typing import List, Optional
import pytz
import uuid
from supabase import Client

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, BackgroundTasks

from app.core.config import settings, supabase
from app.core.deps import get_current_user, get_supabase
from app.core.media import delete_file, upload_base64_image, upload_file
from app.core.moderation import moderate_challenge
from app.schemas.base64 import Base64Images
from app.schemas.challenges import (ChallengeBase, ChallengeCreate,
                                    ChallengeOut, ChallengeParticipantOut,
                                    ChallengeUpdate, ParticipationStatus)
from app.schemas.posts import PostOut
from app.services.scheduler import create_scheduler_job, delete_scheduler_job, get_scheduler_client
from app.services.notifications import send_fcm_notification
from app.schemas.users import UserOut

router = APIRouter(tags=["challenges"])
embedding_model = settings.EMBEDDING_MODEL

def get_embedding(text: str) -> list[float]:
    return embedding_model.encode(text).tolist()

def _cancel_participant_notifications(user_id: str, challenge_id: str, client, db_client):
    """Fetches and deletes all of a single participant's jobs for a challenge."""
    try:
        job_record_resp = db_client.table("participant_jobs").select("scheduler_job_ids").eq("user_id", user_id).eq("challenge_id", challenge_id).single().execute()
        if job_record_resp.data and job_record_resp.data.get("scheduler_job_ids"):
            job_ids = job_record_resp.data["scheduler_job_ids"]
            if isinstance(job_ids, dict):
                for job_name in job_ids.values():
                    delete_scheduler_job(client, job_name)
            # Clean up the record
            db_client.table("participant_jobs").delete().eq("user_id", user_id).eq("challenge_id", challenge_id).execute()
    except Exception as e:
        print(f"Error cancelling notifications for user {user_id} in challenge {challenge_id}: {e}")


def _schedule_participant_notifications(user, challenge: dict, client, db_client):
    """Schedules all notifications for a single participant based on their timezone."""
    job_ids = {}
    checkin_time = challenge.get("check_in_time")
    user_timezone = user.timezone or 'UTC'

    if not checkin_time:
        return

    try:
        # Convert the TIME string from DB into a time object
        local_checkin_time = datetime.strptime(checkin_time, '%H:%M:%S').time()
        
        # Combine with today's date to create a datetime object for timezone conversion
        user_tz = pytz.timezone(user_timezone)
        today = date.today()
        local_dt = user_tz.localize(datetime.combine(today, local_checkin_time))
        
        # Convert to UTC for scheduling
        utc_checkin_time = local_dt.astimezone(pytz.utc)

        # Check-in reminder
        cron_schedule = f"{utc_checkin_time.minute} {utc_checkin_time.hour} * * *"
        job_id = f"challenge-{challenge['id']}-user-{user.id}-checkin-{uuid.uuid4()}"
        payload = {"challenge_id": challenge['id'], "user_id": user.id, "type": "checkin"}
        job_name = create_scheduler_job(client, job_id, cron_schedule, "UTC", payload)
        if job_name:
            job_ids["checkin"] = job_name
        if job_ids:
            db_client.table("participant_jobs").upsert({
                "challenge_id": challenge['id'],
                "user_id": user.id,
                "scheduler_job_ids": job_ids
            }).execute()

    except Exception as e:
        print(f"Error scheduling notifications for user {user.id}: {e}")


@router.post("/", response_model=ChallengeOut, status_code=status.HTTP_201_CREATED)
async def create_challenge(payload: ChallengeCreate, user=Depends(get_current_user), supabase=Depends(get_supabase)):
    """
    Create a new challenge.
    
    Args:
        payload (ChallengeCreate): Challenge data to create
        user: Current authenticated user from token
        
    Returns:
        ChallengeOut: Created challenge data
        
    Raises:
        HTTPException: 400 if creation fails or content is flagged
        HTTPException: 403 if content violates moderation policy
    """
    try:
        #if payload.description:
        #    await moderate_challenge(payload.description, raise_exception=True)
        
        record = payload.model_dump(exclude={"user_timezone"})
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        record.update({"creator_id": user.id, "created_at": now, "updated_at": now})
        
        if record.get("check_in_time"):
            record["check_in_time"] = record["check_in_time"].strftime("%H:%M:%S")
        if record.get("checkin_time"):
             record["checkin_time"] = record["checkin_time"].isoformat()
        if record.get("due_date"):
            record["due_date"] = record["due_date"].isoformat()
        
        if record.get("embedding") is None:
            title = record.get("title", "")
            description = record.get("description", "")
            location = record.get("location", "")
            string_to_vectorize = f"{title}\n{description}\n{location}"
            content_embedding = get_embedding(string_to_vectorize)
            record["embedding"] = content_embedding
        
        
        resp = supabase.table("challenges").insert(record).execute()

        if not resp.data:
            raise HTTPException(status_code=400, detail="Failed to create challenge")
        
        new_challenge = resp.data[0]
        
        return new_challenge
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating challenge: {str(e)}")

@router.get("/", response_model=list[ChallengeOut])
async def list_challenges():
    """
    List all challenges.
    
    Returns:
        list[ChallengeOut]: List of challenge objects
    """
    try:
        resp = supabase.table("challenges").select("*").execute()
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching challenges: {str(e)}")

@router.get("/{challenge_id}", response_model=ChallengeOut)
async def get_challenge(challenge_id: str):
    """
    Get a specific challenge by ID.
    
    Args:
        challenge_id (str): UUID of the challenge to retrieve
        
    Returns:
        ChallengeOut: Challenge data
        
    Raises:
        HTTPException: 404 if challenge not found
    """
    try:
        resp = supabase.table("challenges").select("*").eq("id", challenge_id).single().execute()
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=404, detail="Challenge not found")

@router.put("/{challenge_id}", response_model=ChallengeOut)
async def update_challenge(
    challenge_id: str,
    payload: ChallengeUpdate,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    supabase_client: Client = Depends(get_supabase)
):
    existing_challenge_resp = supabase_client.table("challenges").select("*").eq("id", challenge_id).single().execute()
    if not existing_challenge_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

    existing_challenge = existing_challenge_resp.data
    if existing_challenge["creator_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this challenge")

    update_data = payload.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")

    if "check_in_time" in update_data and update_data["check_in_time"]:
        update_data["check_in_time"] = update_data["check_in_time"].strftime("%H:%M:%S")
        
        def reschedule_all_participants():
            print(f"Background task: Rescheduling all participants for challenge {challenge_id}")
            participants_resp = supabase_client.table("challenge_participants").select("user_id").eq("challenge_id", challenge_id).execute()
            if not participants_resp.data:
                return

            challenge_resp = supabase_client.table("challenges").select("*").eq("id", challenge_id).single().execute()
            if not challenge_resp.data:
                return
            
            scheduler_client = get_scheduler_client()
            for participant in participants_resp.data:
                user_resp = supabase_client.table("users").select("id, timezone").eq("id", participant['user_id']).single().execute()
                if user_resp.data:
                    user_obj = UserOut(**user_resp.data)
                    _cancel_participant_notifications(user_obj.id, challenge_id, scheduler_client, supabase_client)
                    _schedule_participant_notifications(user_obj, challenge_resp.data, scheduler_client, supabase_client)
            print(f"Background task: Finished rescheduling for challenge {challenge_id}")

        background_tasks.add_task(reschedule_all_participants)

    # Handle background photo deletion
    current_background_photo = existing_challenge.get("background_photo")
    if "background_photo" in update_data:
        new_background_photo = update_data["background_photo"]
        if current_background_photo and isinstance(current_background_photo, list) and len(current_background_photo) == 2:
            if new_background_photo != current_background_photo:
                try:
                    delete_file(bucket_name=current_background_photo[0], file_path=current_background_photo[1])
                except Exception as e_del:
                    print(f"Failed to delete old background photo {current_background_photo}: {e_del}")
    
    if update_data.get("checkin_time"):
        update_data["checkin_time"] = update_data["checkin_time"].isoformat()
    
    # Re-calculate embedding
    challenge_for_embedding = {**existing_challenge, **update_data}
    title = challenge_for_embedding.get("title", "")
    description = challenge_for_embedding.get("description", "")
    location = challenge_for_embedding.get("location", "")
    embedding_str = f"{title}\n{description}\n{location}"
    embedding_vector = get_embedding(embedding_str)
    update_data["embedding"] = embedding_vector

    supabase_client.table("challenges").update(update_data).eq("id", challenge_id).execute()
    
    updated_challenge_resp = supabase_client.table("challenges").select("*").eq("id", challenge_id).single().execute()
    return updated_challenge_resp.data

@router.delete("/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_challenge(challenge_id: str, user=Depends(get_current_user), supabase_client: Client = Depends(get_supabase)):
    """
    Delete a challenge.
    
    Args:
        challenge_id (str): UUID of the challenge to delete
        user: Current authenticated user from token
        
    Returns:
        None
        
    Raises:
        HTTPException: 403 if user is not the challenge creator
        HTTPException: 404 if challenge not found
    """
    try:
        challenge_to_delete_resp = supabase_client.table("challenges").select("creator_id, background_photo").eq("id", challenge_id).single().execute()
        
        if not challenge_to_delete_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
            
        challenge_to_delete = challenge_to_delete_resp.data
        if challenge_to_delete["creator_id"] != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this challenge")
        
        all_participant_jobs_resp = supabase_client.table("participant_jobs").select("user_id").eq("challenge_id", challenge_id).execute()
        if all_participant_jobs_resp.data:
            client = get_scheduler_client()
            for record in all_participant_jobs_resp.data:
                _cancel_participant_notifications(record['user_id'], challenge_id, client, supabase_client)

        background_photo_to_delete = challenge_to_delete.get("background_photo")
        if background_photo_to_delete and isinstance(background_photo_to_delete, list) and len(background_photo_to_delete) == 2:
            try:
                delete_file(bucket_name=background_photo_to_delete[0], file_path=background_photo_to_delete[1])
            except Exception as e_del:
                print(f"Failed to delete background photo {background_photo_to_delete} for challenge {challenge_id}: {e_del}")
        
        supabase_client.table("challenges").delete().eq("id", challenge_id).execute()
        return None
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=404, detail="Challenge not found")

@router.post("/{challenge_id}/join", response_model=ChallengeParticipantOut, status_code=status.HTTP_201_CREATED)
async def join_challenge(challenge_id: str, user=Depends(get_current_user), supabase_client: Client = Depends(get_supabase)):
    challenge_resp = supabase_client.table("challenges").select("*").eq("id", challenge_id).single().execute()
    if not challenge_resp.data:
        raise HTTPException(status_code=404, detail="Challenge not found")
        
    existing_participant = supabase_client.table("challenge_participants").select("user_id").eq("challenge_id", challenge_id).eq("user_id", user.id).execute()
    if existing_participant.data:
        raise HTTPException(status_code=400, detail="Already joined this challenge")

    participant_data = { "challenge_id": challenge_id, "user_id": user.id }
    insert_resp = supabase_client.table("challenge_participants").insert(participant_data).execute()
    if not insert_resp.data:
        raise HTTPException(status_code=400, detail="Failed to join challenge")

    client = get_scheduler_client()
    _schedule_participant_notifications(user, challenge_resp.data, client, supabase_client)
    
    # Need to fetch the full participant record to return
    new_participant_resp = supabase_client.table("challenge_participants").select("*").eq("challenge_id", challenge_id).eq("user_id", user.id).single().execute()
    return new_participant_resp.data

@router.delete("/{challenge_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_challenge(challenge_id: str, user=Depends(get_current_user), supabase_client: Client = Depends(get_supabase)):
    client = get_scheduler_client()
    _cancel_participant_notifications(user.id, challenge_id, client, supabase_client)

    supabase_client.table("challenge_participants").delete().eq("challenge_id", challenge_id).eq("user_id", user.id).execute()
    return None

@router.get("/{challenge_id}/participants", response_model=list[ChallengeParticipantOut])
async def list_challenge_participants(challenge_id: str):
    """
    List all participants of a challenge.
    
    Args:
        challenge_id (str): UUID of the challenge
        
    Returns:
        list[ChallengeParticipantOut]: List of challenge participants
        
    Raises:
        HTTPException: 404 if challenge not found
    """
    try:
        challenge = supabase.table("challenges").select("id").eq("id", challenge_id).single().execute()
        if not challenge.data:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        resp = supabase.table("challenge_participants") \
            .select("*") \
            .eq("challenge_id", challenge_id) \
            .execute()
            
        return resp.data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Error fetching challenge participants: {str(e)}")

@router.put("/{challenge_id}/status", response_model=ChallengeParticipantOut)
async def update_participation_status(
    challenge_id: str, 
    status: ParticipationStatus,
    user=Depends(get_current_user)
):
    """
    Update participation status in a challenge.
    
    Args:
        challenge_id (str): UUID of the challenge
        status (ParticipationStatus): New participation status
        user: Current authenticated user from token
        
    Returns:
        ChallengeParticipantOut: Updated challenge participant data
        
    Raises:
        HTTPException: 404 if challenge not found or user is not a participant
    """
    try:
        existing = supabase.table("challenge_participants") \
            .select("*") \
            .eq("challenge_id", challenge_id) \
            .eq("user_id", user.id) \
            .execute()
            
        if not existing.data:
            raise HTTPException(status_code=404, detail="Not a participant in this challenge")
        
        update_data = {"status": status}
        resp = supabase.table("challenge_participants") \
            .update(update_data) \
            .eq("challenge_id", challenge_id) \
            .eq("user_id", user.id) \
            .execute()
            
        if not resp.data:
            raise HTTPException(status_code=400, detail="Failed to update status")
            
        return resp.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Error updating status: {str(e)}")

@router.get("/my/participating", response_model=list[ChallengeOut])
async def get_my_participating_challenges(user=Depends(get_current_user)):
    """
    Get all challenges the current user is participating in.
    
    Args:
        user: Current authenticated user from token
        
    Returns:
        list[ChallengeOut]: List of challenges the user is participating in
    """
    try:
        participants = supabase.table("challenge_participants") \
            .select("challenge_id") \
            .eq("user_id", user.id) \
            .execute()
            
        if not participants.data:
            return []
            
        challenge_ids = [p["challenge_id"] for p in participants.data]
        
        resp = supabase.table("challenges") \
            .select("*") \
            .in_("id", challenge_ids) \
            .execute()
            
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching challenges: {str(e)}")

@router.get("/my/created", response_model=list[ChallengeOut])
async def get_my_created_challenges(user=Depends(get_current_user)):
    """
    Get all challenges created by the current user.
    
    Args:
        user: Current authenticated user from token
        
    Returns:
        list[ChallengeOut]: List of challenges created by the user
    """
    try:
        resp = supabase.table("challenges") \
            .select("*") \
            .eq("creator_id", user.id) \
            .execute()
            
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching challenges: {str(e)}")

@router.post("/{challenge_id}/background-photo", response_model=ChallengeOut)
async def upload_challenge_background_photo(
    challenge_id: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """
    Upload or update the background photo for a challenge.
    The user must be the creator of the challenge.
    """
    challenge_resp = supabase.table("challenges") \
        .select("creator_id, background_photo") \
        .eq("id", challenge_id) \
        .single() \
        .execute()

    if not challenge_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

    if challenge_resp.data["creator_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this challenge's photo")

    old_background_photo = challenge_resp.data.get("background_photo")
    if old_background_photo and isinstance(old_background_photo, list) and len(old_background_photo) == 2:
        try:
            delete_file(bucket_name=old_background_photo[0], file_path=old_background_photo[1])
        except Exception as e:
            print(f"Failed to delete old background photo {old_background_photo}: {str(e)}")

    uploaded_filename = await upload_file("background_photo", file, f"challenge_{challenge_id}_{user.id}")
    new_photo_data = ["background_photo", uploaded_filename]

    updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    supabase.table("challenges") \
        .update({
            "background_photo": new_photo_data,
            "updated_at": updated_at
        }) \
        .eq("id", challenge_id) \
        .execute()

    return supabase.table("challenges") \
        .select("*") \
        .eq("id", challenge_id) \
        .single() \
        .execute().data

@router.get("/{challenge_id}/posts", response_model=List[PostOut])
async def list_posts_for_challenge(challenge_id: str, supabase=Depends(get_supabase)):
    """
    List all posts for a specific challenge.
    
    Args:
        challenge_id (str): UUID of the challenge
        supabase: Supabase client dependency
        
    Returns:
        list[PostOut]: List of post objects
        
    Raises:
        HTTPException: 404 if challenge not found
        HTTPException: 500 for other errors
    """
    try:
        challenge_resp = supabase.table("challenges").select("id").eq("id", challenge_id).single().execute()
        if not challenge_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

        posts_resp = supabase.table("posts").select("*").eq("challenge_id", challenge_id).execute()
        
        if posts_resp.data is None:
            return []

        return posts_resp.data
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error fetching posts for challenge {challenge_id}: {str(e)}") 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching posts for challenge: {str(e)}")

@router.get("/{challenge_id}/ranking/{metric}", response_model=list[ChallengeParticipantOut])
async def get_challenge_ranking(challenge_id: str, metric: str, supabase=Depends(get_supabase)):
    valid_metrics = ["points", "check_ins", "streak"]

    if metric not in valid_metrics:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ranking metric.")

    try:
        challenge = supabase.table("challenges").select("id").eq("id", challenge_id).single().execute()
        if not challenge.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
        
        resp = supabase.table("challenge_participants") \
            .select("*") \
            .eq("challenge_id", challenge_id) \
            .order(metric, desc=True) \
            .execute()
            
        return resp.data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching challenge ranking: {str(e)}")
    
@router.post("/media/base64", response_model=List[List[str]])
async def upload_post_media_base64(
    payload: Base64Images,
    user=Depends(get_current_user)
):
    """
    Upload base64 encoded media for a Challenge.

    Args:
        payload: JSON body containing a list of base64 image strings
        user: Current authenticated user from token

    Returns:
        List[List[str]]: List of [bucket, filename] pairs of the uploaded media

    Raises:
        HTTPException: 400 if upload fails
    """
    processed_media_items = []
    uploaded_filenames_for_cleanup = []
    try:
        for image_data in payload.base64_images:
            filename = await upload_base64_image("challenges", image_data, user.id, "image/jpg")
            processed_media_items.append(["challenges", filename])
            uploaded_filenames_for_cleanup.append(filename)

        return processed_media_items

    except Exception as e:
        for fname in uploaded_filenames_for_cleanup:
            try:
                delete_file("media_urls", fname)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=f"Failed to upload media: {str(e)}")


@router.get("/search/challenges", response_model=list[ChallengeOut])
async def vector_search(
    query: str
):
    """
    Searching for Challenges

    Args:
        query: search keyword

    Returns:
        List[ChallengeOut]

    Raises:
        HTTPException: 500 if search fails
    """

    try:
        query_embedding = get_embedding(query)
        #print(query_embedding)

        resp = supabase.rpc("search_challenges", {"query_embedding": query_embedding}).execute()

        #print("Raw Response from Supabase:", resp)
        return resp.data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/challenge/embeddings", response_model=list[ChallengeOut])
async def update_embeddings():
    try:
        resp = supabase.table("challenges").select("*").execute()
        for challenge in resp.data:
            combined_str = f"{challenge["title"]} {challenge["description"]} {challenge["location"]}"
            content_embedding = get_embedding(combined_str)
            challenge["embedding"] = content_embedding
            respond = supabase.table("challenges").update(challenge).eq("id", challenge["id"]).execute()
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating embeddings {str(e)}")

@router.post("/{challenge_id}/test-notification", status_code=status.HTTP_200_OK)
async def test_challenge_notification(challenge_id: str, user=Depends(get_current_user)):
    """
    Sends a test notification to the challenge creator.
    """
    challenge_resp = supabase.table("challenges").select("title").eq("id", challenge_id).single().execute()
    if not challenge_resp.data:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    if not user.fcm_token:
        raise HTTPException(status_code=400, detail="User does not have an FCM token.")

    send_fcm_notification(
        token=user.fcm_token,
        title="Test Notification",
        body=f"This is a test notification for the challenge: {challenge_resp.data['title']}",
        data={"challenge_id": challenge_id}
    )
    return {"message": "Test notification sent."}

@router.post("/e2e-test/notifications", status_code=200)
async def run_e2e_notification_test(background_tasks: BackgroundTasks, supabase_client: Client = Depends(get_supabase)):
    
    def e2e_test_task():
        import time
        print("\n--- E2E TEST: STARTING ---")
        
        try:
            # Step 1: Create test users
            print("Step 1: Creating test users...")
            user1_email = f"testuser1_{uuid.uuid4()}@example.com"
            user2_email = f"testuser2_{uuid.uuid4()}@example.com"
            user1 = supabase_client.auth.admin.create_user({"email": user1_email, "password": "password123", "email_confirm": True})
            user2 = supabase_client.auth.admin.create_user({"email": user2_email, "password": "password123", "email_confirm": True})
            
            # Insert into public.users table and set timezones
            user1_payload = {
                "id": user1.user.id, "username": "testuser1", "full_name": "Test User 1", 
                "email": user1_email, "timezone": "America/New_York", 
                "fcm_token": "PASTE_YOUR_REAL_FCM_TOKEN_HERE"
            }
            user2_payload = {
                "id": user2.user.id, "username": "testuser2", "full_name": "Test User 2",
                "email": user2_email, "timezone": "Europe/London", "fcm_token": "dummy-fcm-token-for-user2"
            }
            supabase_client.table("users").insert(user1_payload).execute()
            supabase_client.table("users").insert(user2_payload).execute()
            print(f"  - User 1 (NY): {user1.user.id}")
            print(f"  - User 2 (LON): {user2.user.id}")

            # Step 2: Create a challenge
            print("\nStep 2: Creating challenge...")
            checkin_time = (datetime.now() + timedelta(minutes=2)).strftime("%H:%M:%S")
            challenge_payload = {"title": "E2E Test Challenge", "description": "Test", "creator_id": user1.user.id, "check_in_time": checkin_time}
            challenge_resp = supabase_client.table("challenges").insert(challenge_payload).execute()
            challenge = challenge_resp.data[0]
            challenge_id = challenge['id']
            print(f"  - Challenge created with ID: {challenge_id}")
            print(f"  - Check-in time (local to server): {checkin_time}")

            # Step 3: User 1 joins
            print("\nStep 3: User 1 joining...")
            user1_obj = UserOut(**supabase_client.table("users").select("*").eq("id", user1.user.id).single().execute().data)
            join_challenge_sync(challenge_id, user1_obj, supabase_client)
            print("  - User 1 joined, notifications scheduled.")

            # Step 4: Wait and log
            print("\nStep 4: Waiting for 3 minutes to see logs...")
            time.sleep(180)

            # Step 5: Clean up
            print("\nStep 5: Cleaning up resources...")
            delete_challenge_sync(challenge_id, user1_obj, supabase_client)
            
            # Delete from auth schema
            supabase_client.auth.admin.delete_user(user1.user.id)
            supabase_client.auth.admin.delete_user(user2.user.id)
            print("  - Auth users deleted.")

            # Now delete from public.users table
            supabase_client.table("users").delete().eq("id", user1.user.id).execute()
            supabase_client.table("users").delete().eq("id", user2.user.id).execute()
            print("  - Public users deleted.")

        except Exception as e:
            print(f"--- E2E TEST: FAILED: {e} ---")
        else:
            print("\n--- E2E TEST: COMPLETED SUCCESSFULLY ---")

    def join_challenge_sync(challenge_id, user, db_client):
        db_client.table("challenge_participants").insert({"challenge_id": challenge_id, "user_id": user.id}).execute()
        challenge_data = db_client.table("challenges").select("*").eq("id", challenge_id).single().execute().data
        _schedule_participant_notifications(user, challenge_data, get_scheduler_client(), db_client)

    def delete_challenge_sync(challenge_id, user, db_client):
        all_jobs = db_client.table("participant_jobs").select("user_id").eq("challenge_id", challenge_id).execute().data
        if all_jobs:
            client = get_scheduler_client()
            for record in all_jobs:
                _cancel_participant_notifications(record['user_id'], challenge_id, client, db_client)
        db_client.table("challenges").delete().eq("id", challenge_id).execute()


    background_tasks.add_task(e2e_test_task)
    return {"message": "End-to-end notification test started. Check server logs for progress."}
    