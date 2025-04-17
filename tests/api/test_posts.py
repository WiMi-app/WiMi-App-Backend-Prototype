import json
import uuid
from datetime import datetime, timedelta
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

# Removed helper functions for image metadata


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
        "token": token_data["access_token"]
    }
    
    # Clean up: delete the test user
    supabase.table("users").delete().eq("id", user_id).execute()


@pytest.fixture
def test_post(test_user):
    """Create a test post and return its data"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    post_data = {
        "content": f"Test post content {uuid.uuid4().hex[:8]}",
        "media_urls": ["https://example.com/test-image.jpg"],
        "is_private": False
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


def test_create_post(test_user):
    """Test creating a new post"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    post_data = {
        "content": "Test post content with #hashtag",
        "media_urls": ["https://example.com/test-image.jpg"],
        "is_private": False
    }
    
    response = client.post(
        "/api/v1/posts/",
        headers=headers,
        json=post_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["content"] == post_data["content"]
    assert data["media_urls"] == post_data["media_urls"]
    assert data["user_id"] == test_user["id"]
    assert "created_at" in data
    assert "updated_at" in data
    
    # Clean up: delete the created post
    supabase.table("posts").delete().eq("id", data["id"]).execute()


def test_get_posts(test_user, test_post):
    """Test getting a list of posts"""
    response = client.get("/api/v1/posts/")
    
    assert response.status_code == 200
    
    posts = response.json()
    assert isinstance(posts, list)
    
    # Check if our test post is in the list
    post_found = False
    for post in posts:
        if post["id"] == test_post["id"]:
            post_found = True
            assert post["content"] == test_post["content"]
            assert post["user_id"] == test_post["user_id"]
            
            # Check for additional fields in PostWithDetails
            assert "user" in post
            assert "comments_count" in post
            assert "likes_count" in post
            assert "hashtags" in post
            break
    
    assert post_found, "Test post not found in response"


def test_get_posts_with_user_filter(test_user, test_post):
    """Test getting posts with user_id filter"""
    response = client.get(
        f"/api/v1/posts/?user_id={test_user['id']}"
    )
    
    assert response.status_code == 200
    
    posts = response.json()
    assert isinstance(posts, list)
    assert len(posts) > 0
    
    # Verify all posts belong to the specified user
    for post in posts:
        assert post["user_id"] == test_user["id"]


def test_get_post_by_id(test_post):
    """Test getting a specific post by ID"""
    response = client.get(
        f"/api/v1/posts/{test_post['id']}"
    )
    
    assert response.status_code == 200
    
    post = response.json()
    assert post["id"] == test_post["id"]
    assert post["content"] == test_post["content"]
    assert post["user_id"] == test_post["user_id"]


def test_get_nonexistent_post():
    """Test that attempting to get a nonexistent post returns the correct error"""
    nonexistent_id = str(uuid.uuid4())
    
    response = client.get(
        f"/api/v1/posts/{nonexistent_id}"
    )
    
    # Test passes when we get the expected not found error
    assert response.status_code == 404
    assert f"Post with ID {nonexistent_id} not found" in response.json()["detail"]


def test_update_post(test_user, test_post):
    """Test updating a post"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    update_data = {
        "content": f"Updated content {uuid.uuid4().hex[:8]}"
    }
    
    response = client.put(
        f"/api/v1/posts/{test_post['id']}",
        headers=headers,
        json=update_data
    )
    
    assert response.status_code == 200
    
    updated_post = response.json()
    assert updated_post["id"] == test_post["id"]
    assert updated_post["content"] == update_data["content"]
    assert updated_post["user_id"] == test_post["user_id"]


def test_update_post_unauthorized(second_test_user, test_post):
    """Test that attempting to update another user's post returns the correct error"""
    headers = {"Authorization": f"Bearer {second_test_user['token']}"}
    
    update_data = {
        "content": "This update should fail"
    }
    
    response = client.put(
        f"/api/v1/posts/{test_post['id']}",
        headers=headers,
        json=update_data
    )
    
    # Test passes when we get the expected authorization error
    assert response.status_code == 403
    assert "You can only update your own posts" in response.json()["detail"]


def test_delete_post(test_user):
    """Test deleting a post"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # First create a post
    post_data = {
        "content": f"Post to delete {uuid.uuid4().hex[:8]}",
        "media_urls": ["https://example.com/test-image.jpg"],
        "is_private": False
    }
    
    create_response = client.post(
        "/api/v1/posts/",
        headers=headers,
        json=post_data
    )
    
    assert create_response.status_code == 200
    post_id = create_response.json()["id"]
    
    # Now delete the post
    delete_response = client.delete(
        f"/api/v1/posts/{post_id}",
        headers=headers
    )
    
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "success"
    
    # Verify post is deleted by trying to get it
    get_response = client.get(
        f"/api/v1/posts/{post_id}"
    )
    
    assert get_response.status_code == 404


def test_delete_post_unauthorized(test_user, second_test_user):
    """Test that attempting to delete another user's post returns the correct error"""
    # First user creates a post
    headers_user1 = {"Authorization": f"Bearer {test_user['token']}"}
    
    post_data = {
        "content": f"Post that second user will try to delete {uuid.uuid4().hex[:8]}",
        "media_urls": ["https://example.com/test-image.jpg"],
        "is_private": False
    }
    
    create_response = client.post(
        "/api/v1/posts/",
        headers=headers_user1,
        json=post_data
    )
    
    assert create_response.status_code == 200
    post_id = create_response.json()["id"]
    
    # Second user tries to delete it
    headers_user2 = {"Authorization": f"Bearer {second_test_user['token']}"}
    
    delete_response = client.delete(
        f"/api/v1/posts/{post_id}",
        headers=headers_user2
    )
    
    # Test passes when we get the expected authorization error
    assert delete_response.status_code == 403
    assert "Not authorized to delete this post" in delete_response.json()["detail"]
    
    # Clean up: delete the post properly
    client.delete(
        f"/api/v1/posts/{post_id}",
        headers=headers_user1
    )


def test_save_post(test_user, test_post, second_test_user):
    """Test saving a post"""
    # Second user saves first user's post
    headers = {"Authorization": f"Bearer {second_test_user['token']}"}
    
    save_data = {
        "post_id": test_post["id"]
    }
    
    response = client.post(
        "/api/v1/posts/save",
        headers=headers,
        json=save_data
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "Post saved successfully" in response.json()["message"]


def test_save_already_saved_post(test_user, test_post, second_test_user):
    """Test that attempting to save an already saved post returns the correct error"""
    headers = {"Authorization": f"Bearer {second_test_user['token']}"}
    
    save_data = {
        "post_id": test_post["id"]
    }
    
    # First save
    first_response = client.post(
        "/api/v1/posts/save",
        headers=headers,
        json=save_data
    )
    
    assert first_response.status_code == 200
    
    # Try to save again
    second_response = client.post(
        "/api/v1/posts/save",
        headers=headers,
        json=save_data
    )
    
    # Test passes when we get the expected error for duplicate save
    assert second_response.status_code == 400
    assert "Post already saved" in second_response.json()["detail"]


def test_unsave_post(test_user, test_post, second_test_user):
    """Test unsaving a saved post"""
    headers = {"Authorization": f"Bearer {second_test_user['token']}"}
    
    # First save the post
    save_data = {
        "post_id": test_post["id"]
    }
    
    save_response = client.post(
        "/api/v1/posts/save",
        headers=headers,
        json=save_data
    )
    
    assert save_response.status_code == 200
    
    # Now unsave it
    unsave_response = client.delete(
        f"/api/v1/posts/unsave/{test_post['id']}",
        headers=headers
    )
    
    assert unsave_response.status_code == 200
    assert unsave_response.json()["status"] == "success"
    
    # Verify by trying to save again (which should now succeed)
    save_again_response = client.post(
        "/api/v1/posts/save",
        headers=headers,
        json=save_data
    )
    
    assert save_again_response.status_code == 200


def test_unsave_nonexistent_save(test_user, test_post):
    """Test that attempting to unsave a post that wasn't saved returns the correct error"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # Try to unsave a post that wasn't saved
    response = client.delete(
        f"/api/v1/posts/unsave/{test_post['id']}",
        headers=headers
    )
    
    # Test passes when we get the expected error
    assert response.status_code == 404
    assert "Post not saved" in response.json()["detail"] 