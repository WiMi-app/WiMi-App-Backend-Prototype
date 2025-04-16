import json
import uuid
from datetime import datetime
from typing import Dict

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
def test_challenges(test_user):
    """Create multiple test challenges for the user"""
    # Create 3 test challenges
    challenge_ids = []
    
    for i in range(3):
        challenge_data = {
            "title": f"Test Challenge {i} {uuid.uuid4().hex[:8]}",
            "description": f"Test description for challenge {i}",
            "creator_id": test_user["id"],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "is_private": False,
        }
        
        result = supabase.table("challenges").insert(challenge_data).execute()
        
        if not result.data or len(result.data) == 0:
            pytest.fail(f"Failed to create test challenge {i}")
        
        challenge_ids.append(result.data[0]["id"])
    
    yield challenge_ids
    
    # Clean up: delete all test challenges
    for challenge_id in challenge_ids:
        supabase.table("challenges").delete().eq("id", challenge_id).execute()


@pytest.fixture(scope="module")
def test_second_user():
    """Create a second test user for joining challenges"""
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


def test_get_user_with_challenge_stats(test_user, test_challenges):
    """Test getting user profile with challenge statistics"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    response = client.get(
        f"/api/v1/users/{test_user['username']}",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["username"] == test_user["username"]
    
    # Verify challenge statistics
    assert "created_challenges_count" in data
    assert data["created_challenges_count"] >= len(test_challenges)
    assert "joined_challenges_count" in data
    assert "achievements_count" in data


def test_get_user_created_challenges(test_user, test_challenges):
    """Test getting challenges created by a user"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    response = client.get(
        f"/api/v1/users/{test_user['username']}/created-challenges",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= len(test_challenges)
    
    # Verify each test challenge is in the response
    for challenge_id in test_challenges:
        challenge_found = False
        for challenge in data:
            if challenge["id"] == challenge_id:
                challenge_found = True
                assert challenge["creator_id"] == test_user["id"]
                assert "creator" in challenge
                assert "participant_count" in challenge
                assert "posts_count" in challenge
                break
        
        assert challenge_found, f"Challenge {challenge_id} not found in response"


def test_second_user_joins_challenges(test_second_user, test_challenges):
    """Test second user joining the test challenges"""
    headers = {"Authorization": f"Bearer {test_second_user['token']}"}
    
    # Join each test challenge
    for challenge_id in test_challenges:
        join_data = {
            "challenge_id": challenge_id
        }
        
        response = client.post(
            "/api/v1/challenges/join",
            headers=headers,
            json=join_data
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["challenge_id"] == challenge_id
        assert data["user_id"] == test_second_user["id"]
        assert data["status"] == "active"


def test_get_user_joined_challenges(test_second_user, test_challenges):
    """Test getting challenges joined by a user"""
    headers = {"Authorization": f"Bearer {test_second_user['token']}"}
    
    response = client.get(
        f"/api/v1/users/{test_second_user['username']}/joined-challenges",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= len(test_challenges)
    
    # Verify each test challenge is in the response
    for challenge_id in test_challenges:
        challenge_found = False
        for challenge in data:
            if challenge["id"] == challenge_id:
                challenge_found = True
                assert "creator" in challenge
                assert "participant_count" in challenge
                assert "posts_count" in challenge
                assert challenge["is_joined"] == True
                break
        
        assert challenge_found, f"Challenge {challenge_id} not found in response"


def test_get_achievements(test_second_user, test_challenges):
    """Test completing a challenge and getting achievements"""
    headers = {"Authorization": f"Bearer {test_second_user['token']}"}
    
    # Complete the first challenge
    challenge_id = test_challenges[0]
    status_params = {
        "status": "completed"
    }
    
    response = client.put(
        f"/api/v1/challenges/participant/status?challenge_id={challenge_id}",
        headers=headers,
        params=status_params
    )
    
    assert response.status_code == 200
    
    # Get achievements
    achievements_response = client.get(
        "/api/v1/challenges/achievements",
        headers=headers
    )
    
    assert achievements_response.status_code == 200
    
    achievements = achievements_response.json()
    assert isinstance(achievements, list)
    assert len(achievements) > 0
    
    # Verify the achievement for the completed challenge exists
    achievement_found = False
    for achievement in achievements:
        if achievement["challenge_id"] == challenge_id and achievement["user_id"] == test_second_user["id"]:
            achievement_found = True
            assert achievement["achievement_type"] == "completion"
            break
    
    assert achievement_found, "Achievement for completed challenge not found"


def test_user_profile_shows_updated_stats(test_second_user, test_challenges):
    """Test that user profile shows updated challenge statistics"""
    headers = {"Authorization": f"Bearer {test_second_user['token']}"}
    
    response = client.get(
        f"/api/v1/users/{test_second_user['username']}",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify challenge statistics are updated
    assert data["joined_challenges_count"] >= len(test_challenges)
    assert data["achievements_count"] >= 1  # From completing one challenge 