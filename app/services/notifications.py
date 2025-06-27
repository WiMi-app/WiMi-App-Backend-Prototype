import logging
from typing import Optional

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings

logger = logging.getLogger(__name__)

def initialize_firebase_app():
    """
    Initializes the Firebase Admin SDK using Application Default Credentials.
    This works for both local development (with `gcloud auth`) and Cloud Run.
    """
    if not firebase_admin._apps:
        try:
            # `initialize_app` with no arguments uses ADC
            firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized with Application Default Credentials.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

def send_fcm_notification(
    token: str,
    title: str,
    body: str,
    data: Optional[dict] = None
) -> bool:
    """
    Sends an FCM notification to a specific device.

    Args:
        token: The FCM registration token of the target device.
        title: The title of the notification.
        body: The body of the notification.
        data: A dictionary of data to send with the notification.

    Returns:
        True if the notification was sent successfully, False otherwise.
    """
    initialize_firebase_app()
    
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token,
        data=data or {},
    )

    try:
        response = messaging.send(message)
        logger.info(f"Successfully sent FCM message: {response}")
        return True
    except Exception as e:
        logger.error(f"Failed to send FCM message: {e}")
        return False 