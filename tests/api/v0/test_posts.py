import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from uuid import UUID, uuid4
from app.main import app
from app.schemas.posts import PostCreate, PostUpdate

client = TestClient(app)

# Test data
test_post_data = {
    "content": "Test post content",
    "media_urls": ["https://example.com/image1.jpg"],
    "location": "Test Location",
    "is_private": False
}

@pytest.fixture
def auth_token():
    """Fixture to get authentication token"""
    response = client.post(
        "/api/v0/auth/login",
        data={
            "username": "testuser@example.com",
            "password": "testpassword123"
        }
    )
    return response.json()["access_token"]

@pytest.fixture
def auth_headers(auth_token):
    """Fixture to get authentication headers"""
    return {"Authorization": f"Bearer {auth_token}"}

def test_create_post_success(auth_headers):
    """Test successful post creation"""
    response = client.post(
        "/api/v0/posts/",
        headers=auth_headers,
        json=test_post_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == test_post_data["content"]
    assert data["media_urls"] == test_post_data["media_urls"]
    assert data["location"] == test_post_data["location"]
    assert data["is_private"] == test_post_data["is_private"]
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["edited"] is False

def test_create_post_unauthorized():
    """Test post creation without authentication"""
    response = client.post(
        "/api/v0/posts/",
        json=test_post_data
    )
    assert response.status_code == 401

def test_create_post_invalid_data(auth_headers):
    """Test post creation with invalid data"""
    invalid_data = {
        "content": "",  # Empty content
        "media_urls": ["invalid-url"],  # Invalid URL
        "location": None,
        "is_private": "not-a-boolean"  # Invalid boolean
    }
    response = client.post(
        "/api/v0/posts/",
        headers=auth_headers,
        json=invalid_data
    )
    assert response.status_code == 422  # Validation error

def test_get_posts_success(auth_headers):
    """Test successful posts retrieval"""
    response = client.get(
        "/api/v0/posts/",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "id" in data[0]
        assert "content" in data[0]
        assert "user_id" in data[0]
        assert "created_at" in data[0]

def test_get_posts_with_filters(auth_headers):
    """Test posts retrieval with filters"""
    # Test with user_id filter
    response = client.get(
        "/api/v0/posts/?user_id=123e4567-e89b-12d3-a456-426614174000",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Test with hashtag filter
    response = client.get(
        "/api/v0/posts/?hashtag=test",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Test with challenge_id filter
    response = client.get(
        "/api/v0/posts/?challenge_id=123e4567-e89b-12d3-a456-426614174000",
        headers=auth_headers
    )
    assert response.status_code == 200

def test_get_post_by_id_success(auth_headers):
    """Test successful post retrieval by ID"""
    # First create a post
    create_response = client.post(
        "/api/v0/posts/",
        headers=auth_headers,
        json=test_post_data
    )
    post_id = create_response.json()["id"]
    
    # Then retrieve it
    response = client.get(
        f"/api/v0/posts/{post_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == post_id
    assert data["content"] == test_post_data["content"]

def test_get_post_by_id_not_found(auth_headers):
    """Test post retrieval with non-existent ID"""
    non_existent_id = str(uuid4())
    response = client.get(
        f"/api/v0/posts/{non_existent_id}",
        headers=auth_headers
    )
    assert response.status_code == 404

def test_update_post_success(auth_headers):
    """Test successful post update"""
    # First create a post
    create_response = client.post(
        "/api/v0/posts/",
        headers=auth_headers,
        json=test_post_data
    )
    post_id = create_response.json()["id"]
    
    # Update the post
    update_data = {
        "content": "Updated content",
        "location": "Updated location"
    }
    response = client.put(
        f"/api/v0/posts/{post_id}",
        headers=auth_headers,
        json=update_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == update_data["content"]
    assert data["location"] == update_data["location"]
    assert data["edited"] is True

def test_update_post_unauthorized(auth_headers):
    """Test post update without authentication"""
    post_id = str(uuid4())
    update_data = {"content": "Updated content"}
    response = client.put(
        f"/api/v0/posts/{post_id}",
        json=update_data
    )
    assert response.status_code == 401

def test_update_post_not_found(auth_headers):
    """Test update of non-existent post"""
    non_existent_id = str(uuid4())
    update_data = {"content": "Updated content"}
    response = client.put(
        f"/api/v0/posts/{non_existent_id}",
        headers=auth_headers,
        json=update_data
    )
    assert response.status_code == 404

def test_delete_post_success(auth_headers):
    """Test successful post deletion"""
    # First create a post
    create_response = client.post(
        "/api/v0/posts/",
        headers=auth_headers,
        json=test_post_data
    )
    post_id = create_response.json()["id"]
    
    # Delete the post
    response = client.delete(
        f"/api/v0/posts/{post_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Verify post is deleted
    get_response = client.get(
        f"/api/v0/posts/{post_id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404

def test_delete_post_unauthorized():
    """Test post deletion without authentication"""
    post_id = str(uuid4())
    response = client.delete(f"/api/v0/posts/{post_id}")
    assert response.status_code == 401

def test_delete_post_not_found(auth_headers):
    """Test deletion of non-existent post"""
    non_existent_id = str(uuid4())
    response = client.delete(
        f"/api/v0/posts/{non_existent_id}",
        headers=auth_headers
    )
    assert response.status_code == 404

def test_save_post_success(auth_headers):
    """Test successful post saving"""
    # First create a post
    create_response = client.post(
        "/api/v0/posts/",
        headers=auth_headers,
        json=test_post_data
    )
    post_id = create_response.json()["id"]
    
    # Save the post
    response = client.post(
        "/api/v0/posts/save",
        headers=auth_headers,
        json={"post_id": post_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["id"] == post_id

def test_save_post_already_saved(auth_headers):
    """Test saving an already saved post"""
    # First create and save a post
    create_response = client.post(
        "/api/v0/posts/",
        headers=auth_headers,
        json=test_post_data
    )
    post_id = create_response.json()["id"]
    
    # Save it once
    client.post(
        "/api/v0/posts/save",
        headers=auth_headers,
        json={"post_id": post_id}
    )
    
    # Try to save it again
    response = client.post(
        "/api/v0/posts/save",
        headers=auth_headers,
        json={"post_id": post_id}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Post already saved"

def test_unsave_post_success(auth_headers):
    """Test successful post unsaving"""
    # First create and save a post
    create_response = client.post(
        "/api/v0/posts/",
        headers=auth_headers,
        json=test_post_data
    )
    post_id = create_response.json()["id"]
    
    # Save it
    client.post(
        "/api/v0/posts/save",
        headers=auth_headers,
        json={"post_id": post_id}
    )
    
    # Unsave it
    response = client.delete(
        f"/api/v0/posts/unsave/{post_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["id"] == post_id

def test_get_saved_posts_success(auth_headers):
    """Test successful retrieval of saved posts"""
    response = client.get(
        "/api/v0/posts/saved",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) 