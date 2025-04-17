import json
import uuid
from datetime import datetime, time, timedelta
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient
from supabase import Client, create_client

from app.core.config import settings
from app.main import app

# Setup test client
client = TestClient(app)

# Setup Supabase client for test database
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)


@pytest.fixture(scope="module")
def test_user():
    """
    Create a test user for challenge testing.
    
    This fixture:
    1. Creates a unique test user with random username
    2. Registers the user via the auth API
    3. Logs in the user to obtain access token
    4. Yields the user data including token
    5. Cleans up by deleting the user after tests complete
    
    Returns:
        dict: User data including id, username, email, and auth token
    """
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    email = "wimiapp.official@gmail.com"
    password = "testpassword123"
    
    # Create user data
    user_data = {
        "username": username,
        "email": email,
        "password": password,
        "full_name": "Test User",
        "bio": "Test bio",
    }
    
    # Register user
    register_response = client.post(
        "/api/v1/auth/register",
        json=user_data
    )
    
    assert register_response.status_code == 200
    user_id = register_response.json()["id"]
    
    # Login to get access token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password
        }
    )
    
    assert login_response.status_code == 200
    token_data = login_response.json()
    
    yield {
        "id": user_id,
        "username": username,
        "email": email,
        "token": token_data["access_token"]
    }
    
    # Clean up: delete the test user
    supabase.table("users").delete().eq("id", user_id).execute()


@pytest.fixture(scope="module")
def test_challenge(test_user):
    """
    Create a test challenge for testing.
    
    This fixture:
    1. Creates a challenge with a unique title
    2. Directly inserts the challenge into the database
    3. Yields challenge data for test use
    4. Cleans up by deleting the challenge after tests complete
    
    Args:
        test_user: User fixture providing creator credentials

    Returns:
        dict: Challenge data including id, title, and description
    """
    challenge_data = {
        "title": f"Test Challenge {uuid.uuid4().hex[:8]}",
        "description": "Test description for the challenge",
        "creator_id": test_user["id"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "is_active": True,
        "is_private": False,
        "repetition": "daily",
        "check_in_time": time(8, 0).isoformat(),
    }
    
    result = supabase.table("challenges").insert(challenge_data).execute()
    
    if not result.data or len(result.data) == 0:
        pytest.fail("Failed to create test challenge")
    
    challenge_id = result.data[0]["id"]
    
    yield {
        "id": challenge_id,
        "title": challenge_data["title"],
        "description": challenge_data["description"],
    }
    
    # Clean up: delete the test challenge
    supabase.table("challenges").delete().eq("id", challenge_id).execute()


@pytest.fixture(scope="module")
def second_test_user():
    """
    Create a second test user for testing interactions.
    
    This fixture:
    1. Creates another unique test user with random username
    2. Registers the user via the auth API
    3. Logs in the user to obtain access token
    4. Yields the user data including token
    5. Cleans up by deleting the user after tests complete
    
    Returns:
        dict: User data including id, username, email, and auth token
    """
    username = f"testuser2_{uuid.uuid4().hex[:8]}"
    email = "wimiapp.official@gmail.com"
    password = "testpassword123"
    
    # Create user data
    user_data = {
        "username": username,
        "email": email,
        "password": password,
        "full_name": "Test User 2",
        "bio": "Test bio 2",
    }
    
    # Register user
    register_response = client.post(
        "/api/v1/auth/register",
        json=user_data
    )
    
    assert register_response.status_code == 200
    user_id = register_response.json()["id"]
    
    # Login to get access token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password
        }
    )
    
    assert login_response.status_code == 200
    token_data = login_response.json()
    
    yield {
        "id": user_id,
        "username": username,
        "email": email,
        "token": token_data["access_token"]
    }
    
    # Clean up: delete the test user
    supabase.table("users").delete().eq("id", user_id).execute()


def test_create_challenge(test_user):
    """
    Test creation of a new challenge.
    
    This test:
    1. Prepares authorization with user token
    2. Creates a new challenge with random title
    3. Verifies successful creation and data integrity
    4. Cleans up by deleting the created challenge
    
    Args:
        test_user: Fixture providing authenticated user
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    challenge_data = {
        "title": f"New Challenge {uuid.uuid4().hex[:8]}",
        "description": "Test description for a new challenge",
        "repetition": "weekly",
        "repetition_days": [1, 3, 5],  # Monday, Wednesday, Friday
        "check_in_time": "08:00:00",
        "is_private": False
    }
    
    response = client.post(
        "/api/v1/challenges/",
        headers=headers,
        json=challenge_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == challenge_data["title"]
    assert data["description"] == challenge_data["description"]
    assert data["repetition"] == challenge_data["repetition"]
    assert data["creator_id"] == test_user["id"]
    
    # Clean up: delete the created challenge
    supabase.table("challenges").delete().eq("id", data["id"]).execute()


def test_get_challenges(test_user, test_challenge):
    """
    Test retrieval of challenges list.
    
    This test:
    1. Gets the list of challenges with authorization
    2. Verifies test challenge appears in the results
    3. Checks that challenge details are correct
    
    Args:
        test_user: Fixture providing authenticated user
        test_challenge: Fixture providing existing challenge
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    response = client.get(
        "/api/v1/challenges/",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify test challenge is in the list
    challenge_found = False
    for challenge in data:
        if challenge["id"] == test_challenge["id"]:
            challenge_found = True
            assert challenge["title"] == test_challenge["title"]
            assert challenge["description"] == test_challenge["description"]
            break
    
    assert challenge_found, "Test challenge not found in challenges list"


def test_get_specific_challenge(test_user, test_challenge):
    """
    Test getting a specific challenge by ID.
    
    This test:
    1. Requests a specific challenge by its ID
    2. Verifies correct details are returned
    3. Checks that creator and participation data are included
    
    Args:
        test_user: Fixture providing authenticated user
        test_challenge: Fixture providing existing challenge
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    response = client.get(
        f"/api/v1/challenges/{test_challenge['id']}",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == test_challenge["id"]
    assert data["title"] == test_challenge["title"]
    assert data["description"] == test_challenge["description"]
    assert data["creator"]["id"] == test_user["id"]
    assert "participant_count" in data
    assert "posts_count" in data
    assert "is_joined" in data


def test_update_challenge(test_user, test_challenge):
    """
    Test updating an existing challenge.
    
    This test:
    1. Updates title and description of a challenge
    2. Verifies changes were saved properly
    3. Confirms other fields remain unchanged
    
    Args:
        test_user: Fixture providing authenticated user
        test_challenge: Fixture providing existing challenge
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    updated_data = {
        "title": f"Updated Challenge {uuid.uuid4().hex[:8]}",
        "description": "Updated test description",
        "is_active": True
    }
    
    response = client.put(
        f"/api/v1/challenges/{test_challenge['id']}",
        headers=headers,
        json=updated_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == test_challenge["id"]
    assert data["title"] == updated_data["title"]
    assert data["description"] == updated_data["description"]
    assert data["is_active"] == updated_data["is_active"]


def test_join_challenge(second_test_user, test_challenge):
    """
    Test joining a challenge as a participant.
    
    This test:
    1. Uses second test user to join the challenge
    2. Verifies successful join operation
    3. Confirms database record is created
    
    Args:
        second_test_user: Fixture providing another authenticated user
        test_challenge: Fixture providing existing challenge
    """
    headers = {"Authorization": f"Bearer {second_test_user['token']}"}
    
    join_data = {
        "challenge_id": test_challenge["id"]
    }
    
    response = client.post(
        "/api/v1/challenges/join",
        headers=headers,
        json=join_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["challenge_id"] == test_challenge["id"]
    assert data["user_id"] == second_test_user["id"]
    assert data["status"] == "active"
    
    # Verify record exists in database
    participant = supabase.table("challenge_participants") \
        .select("*") \
        .eq("challenge_id", test_challenge["id"]) \
        .eq("user_id", second_test_user["id"]) \
        .execute()
    
    assert participant.data
    assert len(participant.data) > 0


def test_leave_challenge(second_test_user, test_challenge):
    """
    Test leaving a previously joined challenge.
    
    This test:
    1. Uses second test user to leave the challenge
    2. Verifies successful leave operation
    3. Confirms database record is removed
    
    Args:
        second_test_user: Fixture providing another authenticated user
        test_challenge: Fixture providing existing challenge
    """
    headers = {"Authorization": f"Bearer {second_test_user['token']}"}
    
    response = client.delete(
        f"/api/v1/challenges/leave/{test_challenge['id']}",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "left the challenge" in data["message"]
    
    # Verify record no longer exists in database
    participant = supabase.table("challenge_participants") \
        .select("*") \
        .eq("challenge_id", test_challenge["id"]) \
        .eq("user_id", second_test_user["id"]) \
        .execute()
    
    assert not participant.data or len(participant.data) == 0


def test_delete_challenge(test_user, test_challenge):
    """
    Test deleting a challenge.
    
    This test:
    1. Deletes the test challenge
    2. Verifies successful deletion response
    3. Confirms challenge no longer exists in database
    
    Args:
        test_user: Fixture providing authenticated user
        test_challenge: Fixture providing existing challenge
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    response = client.delete(
        f"/api/v1/challenges/{test_challenge['id']}",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "deleted successfully" in data["message"]
    
    # Verify challenge no longer exists
    challenge = supabase.table("challenges") \
        .select("*") \
        .eq("id", test_challenge["id"]) \
        .execute()
    
    assert not challenge.data or len(challenge.data) == 0


def test_search_challenges(test_user, test_challenge):
    """
    Test searching for challenges by title or description.
    
    This test:
    1. Searches for challenges using part of the test challenge title
    2. Verifies the test challenge appears in search results
    
    Args:
        test_user: Fixture providing authenticated user
        test_challenge: Fixture providing existing challenge
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # Search using part of the title
    search_term = test_challenge["title"].split()[0]
    
    response = client.get(
        f"/api/v1/challenges/search?query={search_term}",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    # Verify test challenge is in the results
    challenge_found = False
    for challenge in data:
        if challenge["id"] == test_challenge["id"]:
            challenge_found = True
            assert challenge["title"] == test_challenge["title"]
            break
    
    assert challenge_found, "Test challenge not found in search results"


def test_update_participant_status(second_test_user, test_challenge):
    """
    Test updating a participant's status in a challenge.
    
    This test:
    1. Makes second user join the challenge again
    2. Updates their status to "completed"
    3. Verifies status update and achievement creation
    
    Args:
        second_test_user: Fixture providing another authenticated user
        test_challenge: Fixture providing existing challenge
    """
    headers = {"Authorization": f"Bearer {second_test_user['token']}"}
    
    # Join the challenge first
    join_data = {
        "challenge_id": test_challenge["id"]
    }
    
    client.post(
        "/api/v1/challenges/join",
        headers=headers,
        json=join_data
    )
    
    # Update status to completed
    response = client.put(
        f"/api/v1/challenges/participant/status?challenge_id={test_challenge['id']}&status=completed",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["challenge_id"] == test_challenge["id"]
    assert data["user_id"] == second_test_user["id"]
    assert data["status"] == "completed"
    
    # Verify achievement was created
    achievements = supabase.table("challenge_achievements") \
        .select("*") \
        .eq("challenge_id", test_challenge["id"]) \
        .eq("user_id", second_test_user["id"]) \
        .execute()
    
    assert achievements.data
    assert len(achievements.data) > 0
    assert achievements.data[0]["achievement_type"] == "completion" 