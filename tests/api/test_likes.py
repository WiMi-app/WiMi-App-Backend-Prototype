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
    email = f"{username}@example.com"  # Use unique email based on username
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
def second_test_user():
    """Create a second test user for testing interactions"""
    username = f"testuser2_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"  # Use unique email based on username
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


@pytest.fixture
def test_post(test_user):
    """Create a test post"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    post_data = {
        "content": f"Test post content {uuid.uuid4().hex[:8]}",
        "media_url": None,
    }
    
    response = client.post(
        "/api/v1/posts/",
        headers=headers,
        json=post_data
    )
    
    assert response.status_code == 200
    post = response.json()
    
    yield {
        "id": post["id"],
        "content": post["content"],
        "user_id": post["user_id"],
    }
    
    # Clean up: delete the test post
    supabase.table("posts").delete().eq("id", post["id"]).execute()


@pytest.fixture
def test_comment(test_user, test_post):
    """Create a test comment on a post"""
    # Create comment in database directly since we don't have comment endpoints yet
    comment_data = {
        "user_id": test_user["id"],
        "post_id": test_post["id"],
        "content": f"Test comment {uuid.uuid4().hex[:8]}",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    
    result = supabase.table("comments").insert(comment_data).execute()
    assert result.data and len(result.data) > 0
    
    comment_id = result.data[0]["id"]
    
    yield {
        "id": comment_id,
        "content": comment_data["content"],
        "user_id": comment_data["user_id"],
        "post_id": comment_data["post_id"],
    }
    
    # Clean up: delete the test comment
    supabase.table("comments").delete().eq("id", comment_id).execute()


def test_like_post(second_test_user, test_post):
    """Test liking a post"""
    headers = {"Authorization": f"Bearer {second_test_user['token']}"}
    
    like_data = {
        "post_id": test_post["id"],
        "comment_id": None
    }
    
    response = client.post(
        "/api/v1/likes/",
        headers=headers,
        json=like_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["user_id"] == second_test_user["id"]
    assert data["post_id"] == test_post["id"]
    assert data["comment_id"] is None
    assert "created_at" in data
    
    # Clean up: delete the like
    supabase.table("likes").delete().eq("id", data["id"]).execute()


def test_like_comment(second_test_user, test_comment):
    """Test liking a comment"""
    headers = {"Authorization": f"Bearer {second_test_user['token']}"}
    
    like_data = {
        "post_id": None,
        "comment_id": test_comment["id"]
    }
    
    response = client.post(
        "/api/v1/likes/",
        headers=headers,
        json=like_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["user_id"] == second_test_user["id"]
    assert data["post_id"] is None
    assert data["comment_id"] == test_comment["id"]
    assert "created_at" in data
    
    # Clean up: delete the like
    supabase.table("likes").delete().eq("id", data["id"]).execute()


def test_like_nonexistent_post(test_user):
    """Test liking a nonexistent post"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    nonexistent_id = str(uuid.uuid4())
    like_data = {
        "post_id": nonexistent_id,
        "comment_id": None
    }
    
    response = client.post(
        "/api/v1/likes/",
        headers=headers,
        json=like_data
    )
    
    assert response.status_code == 404
    assert f"Post with ID {nonexistent_id} not found" in response.json()["detail"]


def test_like_nonexistent_comment(test_user):
    """Test liking a nonexistent comment"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    nonexistent_id = str(uuid.uuid4())
    like_data = {
        "post_id": None,
        "comment_id": nonexistent_id
    }
    
    response = client.post(
        "/api/v1/likes/",
        headers=headers,
        json=like_data
    )
    
    assert response.status_code == 404
    assert f"Comment with ID {nonexistent_id} not found" in response.json()["detail"]


def test_like_already_liked_post(test_user, test_post):
    """Test liking a post that is already liked"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    like_data = {
        "post_id": test_post["id"],
        "comment_id": None
    }
    
    # First like
    first_response = client.post(
        "/api/v1/likes/",
        headers=headers,
        json=like_data
    )
    
    assert first_response.status_code == 200
    first_like_id = first_response.json()["id"]
    
    # Try to like again
    second_response = client.post(
        "/api/v1/likes/",
        headers=headers,
        json=like_data
    )
    
    assert second_response.status_code == 400
    assert "Already liked this content" in second_response.json()["detail"]
    
    # Clean up: delete the like
    supabase.table("likes").delete().eq("id", first_like_id).execute()


def test_unlike_post(test_user, test_post):
    """Test unliking a post"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # First like the post
    like_data = {
        "post_id": test_post["id"],
        "comment_id": None
    }
    
    like_response = client.post(
        "/api/v1/likes/",
        headers=headers,
        json=like_data
    )
    
    assert like_response.status_code == 200
    
    # Now unlike it
    unlike_response = client.delete(
        f"/api/v1/likes/post/{test_post['id']}",
        headers=headers
    )
    
    assert unlike_response.status_code == 200
    assert unlike_response.json()["status"] == "success"
    assert "Post unliked successfully" in unlike_response.json()["message"]
    
    # Verify by checking if we can like again
    relike_response = client.post(
        "/api/v1/likes/",
        headers=headers,
        json=like_data
    )
    
    assert relike_response.status_code == 200
    
    # Clean up: delete the new like
    supabase.table("likes").delete().eq("id", relike_response.json()["id"]).execute()


def test_unlike_nonexistent_post_like(test_user):
    """Test unliking a post that hasn't been liked"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    nonexistent_id = str(uuid.uuid4())
    unlike_response = client.delete(
        f"/api/v1/likes/post/{nonexistent_id}",
        headers=headers
    )
    
    assert unlike_response.status_code == 404
    assert "Like not found" in unlike_response.json()["detail"]


def test_unlike_comment(test_user, test_comment):
    """Test unliking a comment"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # First like the comment
    like_data = {
        "post_id": None,
        "comment_id": test_comment["id"]
    }
    
    like_response = client.post(
        "/api/v1/likes/",
        headers=headers,
        json=like_data
    )
    
    assert like_response.status_code == 200
    
    # Now unlike it
    unlike_response = client.delete(
        f"/api/v1/likes/comment/{test_comment['id']}",
        headers=headers
    )
    
    assert unlike_response.status_code == 200
    assert unlike_response.json()["status"] == "success"
    assert "Comment unliked successfully" in unlike_response.json()["message"]
    
    # Verify by checking if we can like again
    relike_response = client.post(
        "/api/v1/likes/",
        headers=headers,
        json=like_data
    )
    
    assert relike_response.status_code == 200
    
    # Clean up: delete the new like
    supabase.table("likes").delete().eq("id", relike_response.json()["id"]).execute()


def test_unlike_nonexistent_comment_like(test_user):
    """Test unliking a comment that hasn't been liked"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    nonexistent_id = str(uuid.uuid4())
    unlike_response = client.delete(
        f"/api/v1/likes/comment/{nonexistent_id}",
        headers=headers
    )
    
    assert unlike_response.status_code == 404
    assert "Like not found" in unlike_response.json()["detail"] 