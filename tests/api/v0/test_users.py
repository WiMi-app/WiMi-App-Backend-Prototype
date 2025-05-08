import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from uuid import UUID, uuid4
from app.main import app
from app.schemas.users import UserUpdate

client = TestClient(app)

@pytest.fixture
def auth_token():
    """Fixture to get authentication token"""
    response = client.post(
        "/api/v0/auth/login",
        data={
            "username": "alice",  # Using sample data user
            "password": "testpassword123"
        }
    )
    return response.json()["access_token"]

@pytest.fixture
def auth_headers(auth_token):
    """Fixture to get authentication headers"""
    return {"Authorization": f"Bearer {auth_token}"}

def test_get_user_profile_success(auth_headers):
    """Test successful retrieval of user profile"""
    response = client.get(
        "/api/v0/users/profile",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice"  # Verify sample data
    assert "id" in data
    assert "email" in data
    assert "full_name" in data
    assert "bio" in data
    assert "avatar_url" in data
    assert "created_at" in data
    assert "updated_at" in data

def test_get_user_profile_unauthorized():
    """Test retrieval of user profile without authentication"""
    response = client.get("/api/v0/users/profile")
    assert response.status_code == 401

def test_update_user_profile_success(auth_headers):
    """Test successful update of user profile"""
    update_data = {
        "full_name": "Alice Updated",
        "bio": "Updated bio for testing",
        "avatar_url": "avatars/alice_updated.jpg"
    }
    response = client.put(
        "/api/v0/users/profile",
        headers=auth_headers,
        json=update_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == update_data["full_name"]
    assert data["bio"] == update_data["bio"]
    assert data["avatar_url"] == update_data["avatar_url"]

def test_update_user_profile_unauthorized():
    """Test update of user profile without authentication"""
    update_data = {
        "full_name": "Unauthorized Update"
    }
    response = client.put(
        "/api/v0/users/profile",
        json=update_data
    )
    assert response.status_code == 401

def test_update_user_profile_invalid_data(auth_headers):
    """Test update of user profile with invalid data"""
    update_data = {
        "email": "invalid-email",  # Invalid email format
        "username": "a"  # Too short username
    }
    response = client.put(
        "/api/v0/users/profile",
        headers=auth_headers,
        json=update_data
    )
    assert response.status_code == 422  # Validation error

def test_get_user_by_id_success(auth_headers):
    """Test successful retrieval of user by ID"""
    # First get Alice's ID from her profile
    profile_response = client.get(
        "/api/v0/users/profile",
        headers=auth_headers
    )
    user_id = profile_response.json()["id"]
    
    response = client.get(
        f"/api/v0/users/{user_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["username"] == "alice"  # Verify sample data
    assert "email" in data
    assert "full_name" in data
    assert "bio" in data
    assert "avatar_url" in data

def test_get_user_by_id_not_found(auth_headers):
    """Test retrieval of non-existent user"""
    non_existent_id = str(uuid4())
    response = client.get(
        f"/api/v0/users/{non_existent_id}",
        headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_get_user_by_id_unauthorized():
    """Test retrieval of user by ID without authentication"""
    response = client.get(f"/api/v0/users/{uuid4()}")
    assert response.status_code == 401

def test_search_users_success(auth_headers):
    """Test successful user search"""
    response = client.get(
        "/api/v0/users/search",
        headers=auth_headers,
        params={"query": "alice"}  # Search for sample user
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(user["username"] == "alice" for user in data)  # Verify sample data

def test_search_users_empty_query(auth_headers):
    """Test user search with empty query"""
    response = client.get(
        "/api/v0/users/search",
        headers=auth_headers,
        params={"query": ""}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_search_users_unauthorized():
    """Test user search without authentication"""
    response = client.get(
        "/api/v0/users/search",
        params={"query": "test"}
    )
    assert response.status_code == 401

def test_get_user_followers_success(auth_headers):
    """Test successful retrieval of user followers"""
    # First get Alice's ID from her profile
    profile_response = client.get(
        "/api/v0/users/profile",
        headers=auth_headers
    )
    user_id = profile_response.json()["id"]
    
    response = client.get(
        f"/api/v0/users/{user_id}/followers",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Verify sample data followers
    assert any(follower["username"] == "bob" for follower in data)
    assert any(follower["username"] == "carol" for follower in data)

def test_get_user_following_success(auth_headers):
    """Test successful retrieval of users being followed"""
    # First get Alice's ID from her profile
    profile_response = client.get(
        "/api/v0/users/profile",
        headers=auth_headers
    )
    user_id = profile_response.json()["id"]
    
    response = client.get(
        f"/api/v0/users/{user_id}/following",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_follow_user_success(auth_headers):
    """Test successful follow of another user"""
    # First get Bob's ID
    search_response = client.get(
        "/api/v0/users/search",
        headers=auth_headers,
        params={"query": "bob"}
    )
    bob_id = search_response.json()[0]["id"]
    
    response = client.post(
        f"/api/v0/users/{bob_id}/follow",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data

def test_unfollow_user_success(auth_headers):
    """Test successful unfollow of another user"""
    # First get Bob's ID
    search_response = client.get(
        "/api/v0/users/search",
        headers=auth_headers,
        params={"query": "bob"}
    )
    bob_id = search_response.json()[0]["id"]
    
    response = client.delete(
        f"/api/v0/users/{bob_id}/follow",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data

def test_follow_nonexistent_user(auth_headers):
    """Test follow of non-existent user"""
    non_existent_id = str(uuid4())
    response = client.post(
        f"/api/v0/users/{non_existent_id}/follow",
        headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_follow_self(auth_headers):
    """Test follow of self"""
    # First get Alice's ID from her profile
    profile_response = client.get(
        "/api/v0/users/profile",
        headers=auth_headers
    )
    user_id = profile_response.json()["id"]
    
    response = client.post(
        f"/api/v0/users/{user_id}/follow",
        headers=auth_headers
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot follow yourself" 