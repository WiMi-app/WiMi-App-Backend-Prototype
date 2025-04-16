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
def test_post(test_user):
    """Create a test post and return its data"""
    post_data = {
        "content": f"Test post content {uuid.uuid4().hex[:8]}",
        "user_id": test_user["id"],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "edited": False,
        "is_private": False,
        "view_count": 0,
    }
    
    result = supabase.table("posts").insert(post_data).execute()
    
    if not result.data or len(result.data) == 0:
        pytest.fail("Failed to create test post")
    
    post_id = result.data[0]["id"]
    
    yield {
        "id": post_id,
        "content": post_data["content"],
    }
    
    # Clean up: delete the test post
    supabase.table("posts").delete().eq("id", post_id).execute()


def test_add_post_to_challenge(test_user, test_challenge, test_post):
    """Test adding a post to a challenge"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    challenge_post_data = {
        "challenge_id": test_challenge["id"],
        "post_id": test_post["id"],
        "is_check_in": True
    }
    
    response = client.post(
        "/api/v1/challenges/post",
        headers=headers,
        json=challenge_post_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["challenge_id"] == test_challenge["id"]
    assert data["post_id"] == test_post["id"]
    assert data["is_check_in"] == True
    
    # Verify record exists in database
    challenge_post = supabase.table("challenge_posts") \
        .select("*") \
        .eq("challenge_id", test_challenge["id"]) \
        .eq("post_id", test_post["id"]) \
        .execute()
    
    assert challenge_post.data
    assert len(challenge_post.data) > 0


def test_get_challenge_posts(test_user, test_challenge, test_post):
    """Test getting posts for a challenge"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    response = client.get(
        f"/api/v1/challenges/{test_challenge['id']}/posts",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    # Verify test post is in the challenge posts
    post_found = False
    for post in data:
        if post["id"] == test_post["id"]:
            post_found = True
            assert post["content"] == test_post["content"]
            assert "user" in post
            assert "challenge_post_details" in post
            assert post["challenge_post_details"]["challenge_id"] == test_challenge["id"]
            break
    
    assert post_found, "Test post not found in challenge posts"


def test_get_posts_with_challenge_filter(test_user, test_challenge, test_post):
    """Test getting posts filtered by challenge"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    response = client.get(
        f"/api/v1/posts/?challenge_id={test_challenge['id']}",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    # Verify test post is in the filtered posts
    post_found = False
    for post in data:
        if post["id"] == test_post["id"]:
            post_found = True
            assert post["content"] == test_post["content"]
            assert "user" in post
            assert "challenge_info" in post
            assert post["challenge_info"]["challenge"]["id"] == test_challenge["id"]
            break
    
    assert post_found, "Test post not found in filtered posts"


def test_create_post_with_challenge(test_user, test_challenge):
    """Test creating a post and then adding it to a challenge"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # First create a post
    post_data = {
        "content": f"New post for challenge {uuid.uuid4().hex[:8]}",
        "is_private": False
    }
    
    post_response = client.post(
        "/api/v1/posts/",
        headers=headers,
        json=post_data
    )
    
    assert post_response.status_code == 200
    
    post = post_response.json()
    post_id = post["id"]
    
    # Then add the post to the challenge
    challenge_post_data = {
        "challenge_id": test_challenge["id"],
        "post_id": post_id,
        "is_check_in": True
    }
    
    response = client.post(
        "/api/v1/challenges/post",
        headers=headers,
        json=challenge_post_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["challenge_id"] == test_challenge["id"]
    assert data["post_id"] == post_id
    
    # Clean up: delete the post
    supabase.table("posts").delete().eq("id", post_id).execute()


def test_delete_post_removes_challenge_association(test_user, test_challenge):
    """Test that deleting a post also removes its challenge association"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # First create a post
    post_data = {
        "content": f"Post to delete {uuid.uuid4().hex[:8]}",
        "is_private": False
    }
    
    post_response = client.post(
        "/api/v1/posts/",
        headers=headers,
        json=post_data
    )
    
    assert post_response.status_code == 200
    
    post = post_response.json()
    post_id = post["id"]
    
    # Add the post to the challenge
    challenge_post_data = {
        "challenge_id": test_challenge["id"],
        "post_id": post_id,
        "is_check_in": True
    }
    
    response = client.post(
        "/api/v1/challenges/post",
        headers=headers,
        json=challenge_post_data
    )
    
    assert response.status_code == 200
    
    # Verify the association exists
    challenge_post = supabase.table("challenge_posts") \
        .select("*") \
        .eq("challenge_id", test_challenge["id"]) \
        .eq("post_id", post_id) \
        .execute()
    
    assert challenge_post.data and len(challenge_post.data) > 0
    
    # Now delete the post
    delete_response = client.delete(
        f"/api/v1/posts/{post_id}",
        headers=headers
    )
    
    assert delete_response.status_code == 200
    
    # Verify the post is deleted
    deleted_post = supabase.table("posts") \
        .select("*") \
        .eq("id", post_id) \
        .execute()
    
    assert not deleted_post.data or len(deleted_post.data) == 0
    
    # Verify the challenge association is also deleted
    challenge_post_after = supabase.table("challenge_posts") \
        .select("*") \
        .eq("challenge_id", test_challenge["id"]) \
        .eq("post_id", post_id) \
        .execute()
    
    assert not challenge_post_after.data or len(challenge_post_after.data) == 0 