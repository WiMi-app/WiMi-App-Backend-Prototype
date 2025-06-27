import logging
import json
from typing import Dict, Optional

from google.cloud import scheduler_v1
from google.protobuf import field_mask_pb2

from app.core.config import settings

logger = logging.getLogger(__name__)

def get_scheduler_client() -> scheduler_v1.CloudSchedulerClient:
    """Initializes and returns a Cloud Scheduler client."""
    return scheduler_v1.CloudSchedulerClient()

def create_scheduler_job(
    client: scheduler_v1.CloudSchedulerClient,
    job_id: str,
    schedule: str,
    timezone: str,
    payload: Dict
) -> Optional[str]:
    """
    Creates a new scheduler job.

    Args:
        client: The Cloud Scheduler client.
        job_id: The ID for the new job.
        schedule: The cron schedule for the job.
        timezone: The timezone for the schedule.
        payload: The JSON payload to send to the target URL.

    Returns:
        The name of the created job, or None if creation fails.
    """
    parent = f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.GCP_LOCATION}"
    job_name = f"{parent}/jobs/{job_id}"

    job = {
        "name": job_name,
        "schedule": schedule,
        "time_zone": timezone,
        "http_target": {
            "uri": settings.CLOUD_FUNCTION_URL,
            "http_method": scheduler_v1.HttpMethod.POST,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode("utf-8"),
        },
    }

    try:
        created_job = client.create_job(parent=parent, job=job)
        logger.info(f"Created scheduler job: {created_job.name}")
        return created_job.name
    except Exception as e:
        logger.error(f"Failed to create scheduler job {job_id}: {e}")
        return None

def delete_scheduler_job(client: scheduler_v1.CloudSchedulerClient, job_name: str) -> bool:
    """
    Deletes a scheduler job.

    Args:
        client: The Cloud Scheduler client.
        job_name: The full name of the job to delete.

    Returns:
        True if deletion was successful, False otherwise.
    """
    try:
        client.delete_job(name=job_name)
        logger.info(f"Deleted scheduler job: {job_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete scheduler job {job_name}: {e}")
        return False 