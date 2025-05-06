import pytest
import time
from uuid import uuid4
from fastapi import status


@pytest.fixture
def user_profile_update():
    return {
        "bio": "Updated bio",
        "full_name": "Updated Name",
        "avatar_url": "https://example.com/updated_avatar.jpg"
    }


def test_get_current_user(client, auth_headers):
    """Test getting current user profile."""
    # Act
    start_time = time.time()
    response = client.get("/api/v0/users/me", headers=auth_headers)
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "username" in response.json()
    assert "email" in response.json()
    assert "bio" in response.json()
    assert duration < 0.005  # Less than 5ms


def test_update_user_profile(client, auth_headers, user_profile_update):
    """Test updating user profile information."""
    # Act
    start_time = time.time()
    response = client.put(
        "/api/v0/users/me", 
        json=user_profile_update,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["bio"] == user_profile_update["bio"]
    assert response.json()["full_name"] == user_profile_update["full_name"]
    assert response.json()["avatar_url"] == user_profile_update["avatar_url"]
    assert duration < 0.005  # Less than 5ms


def test_update_user_profile_unauthorized(client, user_profile_update):
    """Test updating user profile without authentication fails."""
    # Act
    response = client.put("/api/v0/users/me", json=user_profile_update)
    
    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_user_by_username(client, supabase_mock):
    """Test getting user profile by username."""
    # Arrange
    username = supabase_mock.test_users[0]["username"]
    
    # Act
    start_time = time.time()
    response = client.get(f"/api/v0/users/{username}")
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == username
    assert "followers_count" in response.json()
    assert "following_count" in response.json()
    assert "posts_count" in response.json()
    assert duration < 0.005  # Less than 5ms


def test_get_user_not_found(client):
    """Test getting non-existent user returns 404."""
    # Act
    response = client.get("/api/v0/users/nonexistentuser")
    
    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_bio(client, auth_headers):
    """Test updating user bio."""
    # Arrange
    bio_update = {"bio": "This is my new bio"}
    
    # Act
    start_time = time.time()
    response = client.put(
        "/api/v0/users/me", 
        json=bio_update,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["bio"] == bio_update["bio"]
    assert duration < 0.002  # Less than 2ms


def test_update_name(client, auth_headers):
    """Test updating user full name."""
    # Arrange
    name_update = {"full_name": "New Full Name"}
    
    # Act
    start_time = time.time()
    response = client.put(
        "/api/v0/users/me", 
        json=name_update,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["full_name"] == name_update["full_name"]
    assert duration < 0.002  # Less than 2ms


def test_update_username(client, auth_headers):
    """Test updating username."""
    # Arrange
    username_update = {"username": "newusername"}
    
    # Act
    start_time = time.time()
    response = client.put(
        "/api/v0/users/me", 
        json=username_update,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == username_update["username"]
    assert duration < 0.002  # Less than 2ms


def test_update_profile_picture(client, auth_headers):
    """Test updating profile picture URL."""
    # Arrange
    pfp_update = {"avatar_url": "https://example.com/new_profile_pic.jpg"}
    
    # Act
    start_time = time.time()
    response = client.put(
        "/api/v0/users/me", 
        json=pfp_update,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["avatar_url"] == pfp_update["avatar_url"]
    assert duration < 0.005  # Less than 5ms


def test_follow_user(client, auth_headers, supabase_mock):
    """Test following another user."""
    # Arrange
    followed_user_id = str(uuid4())
    # Add the user to be followed
    supabase_mock.tables["users"].data.append({
        "id": followed_user_id,
        "username": "usertofollow",
        "email": "follow@example.com",
    })
    
    follow_data = {"followed_id": followed_user_id}
    
    # Act
    start_time = time.time()
    response = client.post(
        "/api/v0/users/follow", 
        json=follow_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["followed_id"] == followed_user_id
    assert duration < 0.005  # Less than 5ms
    
    # Check that a notification was created
    follows = [f for f in supabase_mock.tables["follows"].data 
              if f["followed_id"] == followed_user_id]
    assert len(follows) == 1
    

def test_unfollow_user(client, auth_headers, supabase_mock):
    """Test unfollowing a user."""
    # Arrange
    followed_user_id = str(uuid4())
    # Add the follow relationship
    follower_id = supabase_mock.test_users[0]["id"]
    supabase_mock.tables["follows"].data.append({
        "id": str(uuid4()),
        "follower_id": follower_id,
        "followed_id": followed_user_id,
        "created_at": "2023-01-01T00:00:00"
    })
    
    # Act
    start_time = time.time()
    response = client.delete(
        f"/api/v0/users/unfollow/{followed_user_id}", 
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.005  # Less than 5ms


def test_update_user_validation_errors(client, auth_headers):
    """Test user update fails with appropriate errors when data is invalid."""
    # Test various validation scenarios
    test_cases = [
        # Empty username
        {
            "data": {"username": ""},
            "expected_error": "Username cannot be empty"
        },
        # Username too short
        {
            "data": {"username": "a"},
            "expected_error": "Username must be at least"
        },
        # Invalid email format
        {
            "data": {"email": "not-an-email"},
            "expected_error": "Invalid email format"
        },
        # Invalid bio length (if there's a limit)
        {
            "data": {"bio": "x" * 1000},  # Assuming there's a reasonable limit
            "expected_error": "Bio exceeds maximum length"
        }
    ]
    
    for test_case in test_cases:
        # Act
        response = client.put(
            "/api/v0/users/me", 
            json=test_case["data"],
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert test_case["expected_error"] in response.json()["detail"] 