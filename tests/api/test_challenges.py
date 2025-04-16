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
    """Create a test user and return credentials"""
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "testpassword123"
    
    # Create test user
    user_data = {
        "username": username,
        "email": email,
        "password": password,
        "full_name": "Test User",
        "bio": "Test bio",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    result = supabase.table("users").insert(user_data).execute()
    
    if not result.data or len(result.data) == 0:
        pytest.fail("Failed to create test user")
    
    user_id = result.data[0]["id"]
    
    # Login to get access token
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password}
    )
    
    if login_response.status_code != 200:
        pytest.fail("Failed to log in test user")
    
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
    """Create a test challenge and return its data"""
    challenge_data = {
        "title": f"Test Challenge {uuid.uuid4().hex[:8]}",
        "description": "Test description for the challenge",
        "creator_id": test_user["id"],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
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
def test_second_user():
    """Create a second test user for testing interactions"""
    username = f"testuser2_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "testpassword123"
    
    # Create test user
    user_data = {
        "username": username,
        "email": email,
        "password": password,
        "full_name": "Test User 2",
        "bio": "Test bio 2",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    result = supabase.table("users").insert(user_data).execute()
    
    if not result.data or len(result.data) == 0:
        pytest.fail("Failed to create second test user")
    
    user_id = result.data[0]["id"]
    
    # Login to get access token
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password}
    )
    
    if login_response.status_code != 200:
        pytest.fail("Failed to log in second test user")
    
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
    """Test creating a new challenge"""
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
    
    # Clean up: delete the created challenge
    supabase.table("challenges").delete().eq("id", data["id"]).execute()


def test_get_challenges(test_user, test_challenge):
    """Test getting a list of challenges"""
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
    
    assert challenge_found, "Test challenge not found in response"


def test_get_challenge_by_id(test_user, test_challenge):
    """Test getting a specific challenge by ID"""
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
    
    # Verify additional details are present
    assert "creator" in data
    assert "participant_count" in data
    assert "posts_count" in data
    assert "is_joined" in data


def test_update_challenge(test_user, test_challenge):
    """Test updating a challenge"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    update_data = {
        "title": f"Updated Challenge {uuid.uuid4().hex[:8]}",
        "description": "Updated description"
    }
    
    response = client.put(
        f"/api/v1/challenges/{test_challenge['id']}",
        headers=headers,
        json=update_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["description"] == update_data["description"]


def test_join_challenge(test_second_user, test_challenge):
    """Test joining a challenge"""
    headers = {"Authorization": f"Bearer {test_second_user['token']}"}
    
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
    assert data["user_id"] == test_second_user["id"]
    assert data["status"] == "active"


def test_get_challenge_participants(test_user, test_challenge, test_second_user):
    """Test getting challenge participants"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    response = client.get(
        f"/api/v1/challenges/{test_challenge['id']}/participants",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    # Verify second user is in the participants list
    participant_found = False
    for participant in data:
        if participant["user_id"] == test_second_user["id"]:
            participant_found = True
            assert "user" in participant
            assert participant["user"]["id"] == test_second_user["id"]
            break
    
    assert participant_found, "Second test user not found in participants"


def test_update_participant_status(test_second_user, test_challenge):
    """Test updating participant status"""
    headers = {"Authorization": f"Bearer {test_second_user['token']}"}
    
    status_params = {
        "status": "completed"
    }
    
    response = client.put(
        f"/api/v1/challenges/participant/status?challenge_id={test_challenge['id']}",
        headers=headers,
        params=status_params
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "completed"
    
    # Verify achievement was created
    achievements = supabase.table("challenge_achievements") \
        .select("*") \
        .eq("challenge_id", test_challenge["id"]) \
        .eq("user_id", test_second_user["id"]) \
        .execute()
    
    assert achievements.data
    assert len(achievements.data) > 0
    assert achievements.data[0]["achievement_type"] == "completion"


def test_search_challenges(test_user, test_challenge):
    """Test searching for challenges"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # Search by partial title
    partial_title = test_challenge["title"].split()[0]
    
    response = client.get(
        f"/api/v1/challenges/search?query={partial_title}",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    # Verify test challenge is in the search results
    challenge_found = False
    for challenge in data:
        if challenge["id"] == test_challenge["id"]:
            challenge_found = True
            break
    
    assert challenge_found, "Test challenge not found in search results"


def test_trending_challenges(test_user, test_challenge):
    """Test getting trending challenges"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    response = client.get(
        "/api/v1/challenges/trending",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)


def test_leave_challenge(test_second_user, test_challenge):
    """Test leaving a challenge"""
    headers = {"Authorization": f"Bearer {test_second_user['token']}"}
    
    response = client.delete(
        f"/api/v1/challenges/leave/{test_challenge['id']}",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    
    # Verify user is no longer a participant
    participants = supabase.table("challenge_participants") \
        .select("*") \
        .eq("challenge_id", test_challenge["id"]) \
        .eq("user_id", test_second_user["id"]) \
        .execute()
    
    assert not participants.data or len(participants.data) == 0


def test_delete_challenge(test_user, test_challenge):
    """Test deleting a challenge"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    response = client.delete(
        f"/api/v1/challenges/{test_challenge['id']}",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    
    # Verify challenge is deleted
    challenge = supabase.table("challenges") \
        .select("*") \
        .eq("id", test_challenge["id"]) \
        .execute()
    
    assert not challenge.data or len(challenge.data) == 0 