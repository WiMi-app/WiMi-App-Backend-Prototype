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
        "password": password,
        "token": token_data["access_token"]
    }
    
    # Clean up: delete the test user
    supabase.table("users").delete().eq("id", user_id).execute()


@pytest.fixture(scope="module")
def second_test_user():
    """Create a second test user for testing interactions"""
    username = f"testuser2_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
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
        "password": password,
        "token": token_data["access_token"]
    }
    
    # Clean up: delete the test user
    supabase.table("users").delete().eq("id", user_id).execute()


def test_read_user_me(test_user):
    """Test reading current user information"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    response = client.get(
        "/api/v1/users/me",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == test_user["id"]
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    assert "password_hash" not in data  # Ensure password hash is not returned


def test_update_user_me(test_user):
    """Test updating current user information"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    update_data = {
        "full_name": "Updated Name",
        "bio": "Updated bio"
    }
    
    response = client.put(
        "/api/v1/users/me",
        headers=headers,
        json=update_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == test_user["id"]
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    assert data["full_name"] == update_data["full_name"]
    assert data["bio"] == update_data["bio"]


def test_update_user_password(test_user):
    """Test updating current user password"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    new_password = "newpassword123"
    update_data = {
        "password": new_password
    }
    
    response = client.put(
        "/api/v1/users/me",
        headers=headers,
        json=update_data
    )
    
    assert response.status_code == 200
    
    # Try to login with new password
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["email"],
            "password": new_password
        }
    )
    
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


def test_get_user_by_username(test_user):
    """Test getting a user by username"""
    response = client.get(
        f"/api/v1/users/{test_user['username']}",
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == test_user["id"]
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    
    # Check if stats fields are present
    assert "posts_count" in data
    assert "followers_count" in data
    assert "following_count" in data
    assert "created_challenges_count" in data
    assert "joined_challenges_count" in data
    assert "achievements_count" in data


def test_get_user_by_nonexistent_username():
    """Test getting a nonexistent user by username"""
    nonexistent_username = f"nonexistent_{uuid.uuid4().hex[:8]}"
    
    response = client.get(
        f"/api/v1/users/{nonexistent_username}",
    )
    
    assert response.status_code == 404
    assert f"User with username {nonexistent_username} not found" in response.json()["detail"]


def test_get_user_posts(test_user):
    """Test getting user posts"""
    # First create a post for the user
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    post_data = {
        "content": "Test post content",
        "media_url": None,
    }
    
    create_post_response = client.post(
        "/api/v1/posts/",
        headers=headers,
        json=post_data
    )
    
    assert create_post_response.status_code == 200
    post_id = create_post_response.json()["id"]
    
    # Now get user posts
    response = client.get(
        f"/api/v1/users/{test_user['username']}/posts",
    )
    
    assert response.status_code == 200
    
    posts = response.json()
    assert isinstance(posts, list)
    assert len(posts) > 0
    
    # Verify the created post is in the list
    post_found = False
    for post in posts:
        if post["id"] == post_id:
            post_found = True
            assert post["content"] == post_data["content"]
            assert post["user_id"] == test_user["id"]
            break
    
    assert post_found, "Created post not found in user posts"
    
    # Clean up: delete the test post
    supabase.table("posts").delete().eq("id", post_id).execute()


def test_follow_user(test_user, second_test_user):
    """Test following another user"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # Make sure no follow relationship exists before starting
    supabase.table("follows").delete() \
        .eq("follower_id", test_user["id"]) \
        .eq("followed_id", second_test_user["id"]) \
        .execute()
    
    follow_data = {
        "followed_id": second_test_user["id"]
    }
    
    response = client.post(
        "/api/v1/users/follow",
        headers=headers,
        json=follow_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["follower_id"] == test_user["id"]
    assert data["followed_id"] == second_test_user["id"]
    assert "created_at" in data
    
    # Clean up: delete the follow relationship
    supabase.table("follows").delete() \
        .eq("follower_id", test_user["id"]) \
        .eq("followed_id", second_test_user["id"]) \
        .execute()


def test_follow_already_following(test_user, second_test_user):
    """Test following a user that is already being followed"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # Make sure no follow relationship exists before starting
    supabase.table("follows").delete() \
        .eq("follower_id", test_user["id"]) \
        .eq("followed_id", second_test_user["id"]) \
        .execute()
    
    # First follow the user
    follow_data = {
        "followed_id": second_test_user["id"]
    }
    
    first_response = client.post(
        "/api/v1/users/follow",
        headers=headers,
        json=follow_data
    )
    
    assert first_response.status_code == 200
    
    # Try to follow again
    second_response = client.post(
        "/api/v1/users/follow",
        headers=headers,
        json=follow_data
    )
    
    assert second_response.status_code == 400
    assert "Already following this user" in second_response.json()["detail"]
    
    # Clean up: delete the follow relationship
    supabase.table("follows").delete() \
        .eq("follower_id", test_user["id"]) \
        .eq("followed_id", second_test_user["id"]) \
        .execute()


def test_unfollow_user(test_user, second_test_user):
    """Test unfollowing a user"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # Make sure no follow relationship exists before starting
    supabase.table("follows").delete() \
        .eq("follower_id", test_user["id"]) \
        .eq("followed_id", second_test_user["id"]) \
        .execute()
    
    # First follow the user
    follow_data = {
        "followed_id": second_test_user["id"]
    }
    
    follow_response = client.post(
        "/api/v1/users/follow",
        headers=headers,
        json=follow_data
    )
    
    assert follow_response.status_code == 200
    
    # Now unfollow
    unfollow_response = client.delete(
        f"/api/v1/users/unfollow/{second_test_user['id']}",
        headers=headers
    )
    
    assert unfollow_response.status_code == 200
    assert unfollow_response.json()["status"] == "success"
    
    # Verify by trying to follow again (which should now succeed)
    follow_again_response = client.post(
        "/api/v1/users/follow",
        headers=headers,
        json=follow_data
    )
    
    assert follow_again_response.status_code == 200
    
    # Clean up: delete the follow relationship
    supabase.table("follows").delete() \
        .eq("follower_id", test_user["id"]) \
        .eq("followed_id", second_test_user["id"]) \
        .execute() 