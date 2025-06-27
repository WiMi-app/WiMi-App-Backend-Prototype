import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional

import firebase_admin
from firebase_admin import credentials, messaging
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Supabase and Firebase
try:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(supabase_url, supabase_key)
    logging.info("Supabase client initialized.")
except Exception as e:
    logging.error(f"Failed to initialize Supabase client: {e}")
    supabase = None

try:
    # In a Cloud Function environment, ADC will be used automatically
    # if no credential object is provided.
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)
    logging.info("Firebase Admin SDK initialized with Application Default Credentials.")
except Exception as e:
    logging.error(f"Failed to initialize Firebase Admin SDK: {e}")

async def get_user_fcm_token(user_id: str) -> Optional[str]:
    """Fetches a user's FCM token from Supabase asynchronously."""
    if not supabase:
        return None
    try:
        response = await asyncio.to_thread(
            supabase.table("users").select("fcm_token").eq("id", user_id).single().execute
        )
        if response.data and response.data.get("fcm_token"):
            logging.info(f"Retrieved FCM token for user {user_id}")
            return response.data["fcm_token"]
        logging.warning(f"No FCM token found for user {user_id}")
        return None
    except Exception as e:
        logging.error(f"Error fetching FCM token for user {user_id}: {e}")
        return None

async def get_challenge_details(challenge_id: str) -> Optional[Dict[str, Any]]:
    """Fetches challenge details from Supabase asynchronously."""
    if not supabase:
        return None
    try:
        response = await asyncio.to_thread(
            supabase.table("challenges").select("title").eq("id", challenge_id).single().execute
        )
        if response.data:
            logging.info(f"Retrieved details for challenge {challenge_id}")
            return response.data
        logging.warning(f"No details found for challenge {challenge_id}")
        return None
    except Exception as e:
        logging.error(f"Error fetching challenge details for {challenge_id}: {e}")
        return None

def send_fcm_notification(token: str, title: str, body: str, data: Dict[str, str]) -> bool:
    """Sends a single FCM notification."""
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token,
        data=data
    )
    try:
        response = messaging.send(message)
        logging.info(f"Successfully sent FCM message to token {token[:10]}...: {response}")
        return True
    except Exception as e:
        logging.error(f"Failed to send FCM message to token {token[:10]}...: {e}")
        return False

async def process_notification(payload: Dict[str, Any]):
    """Main logic to process a single notification request."""
    challenge_id = payload.get("challenge_id")
    user_id = payload.get("user_id")
    notification_type = payload.get("type")

    if not all([challenge_id, user_id, notification_type]):
        logging.error(f"Invalid payload received: {payload}")
        return

    fcm_token, challenge = await asyncio.gather(
        get_user_fcm_token(user_id),
        get_challenge_details(challenge_id)
    )

    if not fcm_token or not challenge:
        logging.error(f"Could not retrieve token or challenge details for user {user_id} and challenge {challenge_id}")
        return

    title = f"Challenge: {challenge['title']}"
    body = ""
    if notification_type == "checkin":
        body = "It's time to check in for your challenge!"
    elif notification_type == "grace_warning":
        body = "Your check-in is due soon! Don't lose your streak."
    elif notification_type == "final_reminder":
        body = "Final reminder! Your check-in is due in 5 minutes."
    else:
        logging.warning(f"Unknown notification type: {notification_type}")
        return

    send_fcm_notification(fcm_token, title, body, {"challengeId": challenge_id})

def main(request):
    """
    Entry point for the Google Cloud Function.
    Handles an HTTP request and triggers the notification logic.
    """
    if request.method != 'POST':
        return 'Only POST requests are accepted', 405

    try:
        payload = request.get_json()
        if not payload:
            logging.error("No payload received.")
            return 'Bad Request: No JSON payload', 400

        logging.info(f"Received payload: {payload}")
        asyncio.run(process_notification(payload))
        
        return 'Notification processed successfully', 200

    except json.JSONDecodeError:
        logging.error("Invalid JSON received.")
        return 'Bad Request: Invalid JSON', 400
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return 'Internal Server Error', 500 