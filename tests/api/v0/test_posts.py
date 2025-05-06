import pytest
import time
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import status
from datetime import datetime, timedelta

@pytest.fixture
def post_data():
    return {
        "content": "This is a test post with #hashtag",
        "media_urls": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
        "location": "Test Location",
        "is_private": False
    }


@pytest.fixture
def test_post(supabase_mock):
    """Create a test post fixture."""
    post_id = str(uuid4())
    user_id = supabase_mock.test_users[0]["id"]
    
    post = {
        "id": post_id,
        "user_id": user_id,
        "content": "Existing test post with #testtag",
        "media_urls": ["https://example.com/image.jpg"],
        "location": "Test Location",
        "is_private": False,
        "created_at": datetime.now().isoformat() - timedelta(hours=1), # 1 hour ago
        "updated_at": datetime.now().isoformat(),
        "edited": False
    }
    
    supabase_mock.tables["posts"].data.append(post)
    return post


@patch('app.api.v0.posts.moderate_content')
async def test_create_post(mock_moderate_content, client, auth_headers, post_data, supabase_mock):
    """Test creating a new post."""
    # Arrange
    mock_moderate_content.return_value = AsyncMock(flagged=False)
    
    # Act
    start_time = time.time()
    response = client.post(
        "/api/v0/posts/", 
        json=post_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "id" in response.json()
    assert response.json()["content"] == post_data["content"]
    assert len(response.json()["media_urls"]) == len(post_data["media_urls"])
    assert response.json()["location"] == post_data["location"]
    assert duration < 0.005  # Less than 5ms
    
    # Verify hashtag was processed
    hashtags = [h for h in supabase_mock.tables["hashtags"].data if h["name"] == "hashtag"]
    assert len(hashtags) > 0


@patch('app.api.v0.posts.moderate_content')
async def test_create_post_with_moderation_flag(mock_moderate_content, client, auth_headers, post_data):
    """Test creating a post that gets flagged by moderation."""
    # Arrange
    mock_moderate_content.return_value = AsyncMock(flagged=True)
    
    # Act
    response = client.post(
        "/api/v0/posts/", 
        json=post_data,
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "violates community guidelines" in response.json()["detail"]


def test_get_posts(client, test_post):
    """Test getting a list of posts."""
    # Act
    start_time = time.time()
    response = client.get("/api/v0/posts/")
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0
    assert "user" in response.json()[0]  # Should include user data
    assert "comments_count" in response.json()[0]  # Should include counts
    assert duration < 0.005  # Less than 5ms


def test_get_post_by_id(client, test_post):
    """Test getting a specific post by ID."""
    # Act
    start_time = time.time()
    response = client.get(f"/api/v0/posts/{test_post['id']}")
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == test_post["id"]
    assert response.json()["content"] == test_post["content"]
    assert "user" in response.json()
    assert duration < 0.005  # Less than 5ms


def test_get_post_not_found(client):
    """Test getting a non-existent post returns 404."""
    # Act
    response = client.get(f"/api/v0/posts/{uuid4()}")
    
    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


@patch('app.api.v0.posts.moderate_content')
async def test_update_post(mock_moderate_content, client, auth_headers, test_post):
    """Test updating a post."""
    # Arrange
    mock_moderate_content.return_value = AsyncMock(flagged=False)
    update_data = {
        "content": "Updated content with #newtag",
        "media_urls": ["https://example.com/updated.jpg"],
        "location": "Updated Location"
    }
    
    # Act
    start_time = time.time()
    response = client.put(
        f"/api/v0/posts/{test_post['id']}", 
        json=update_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["content"] == update_data["content"]
    assert response.json()["location"] == update_data["location"]
    assert response.json()["edited"] is True
    assert duration < 0.005  # Less than 5ms


def test_delete_post(client, auth_headers, test_post, supabase_mock):
    """Test deleting a post."""
    # Act
    start_time = time.time()
    response = client.delete(
        f"/api/v0/posts/{test_post['id']}",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.005  # Less than 5ms
    
    # Verify post was deleted from mock DB
    posts = [p for p in supabase_mock.tables["posts"].data if p["id"] == test_post["id"]]
    assert len(posts) == 0


def test_save_post(client, auth_headers, test_post, supabase_mock):
    """Test saving a post."""
    # Arrange
    save_data = {"post_id": test_post["id"]}
    
    # Act
    start_time = time.time()
    response = client.post(
        "/api/v0/posts/save",
        json=save_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.005  # Less than 5ms
    
    # Verify saved post in mock DB
    saved_posts = supabase_mock.tables["user_saved_posts"].data
    assert len(saved_posts) > 0
    assert saved_posts[0]["post_id"] == test_post["id"]


def test_unsave_post(client, auth_headers, test_post, supabase_mock):
    """Test unsaving a post."""
    # Arrange - first save the post
    user_id = supabase_mock.test_users[0]["id"]
    supabase_mock.tables["user_saved_posts"].data.append({
        "user_id": user_id,
        "post_id": test_post["id"],
        "created_at": "2023-01-01T00:00:00"
    })
    
    # Act
    start_time = time.time()
    response = client.delete(
        f"/api/v0/posts/unsave/{test_post['id']}",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.005  # Less than 5ms


def test_upload_media(client, auth_headers, supabase_mock):
    """Test media upload for posts."""
    # Mock file upload
    with open("tests/test_files/test_image.jpg", "wb") as f:
        f.write(b"test image content")
    
    # Act
    start_time = time.time()
    with open("tests/test_files/test_image.jpg", "rb") as f:
        files = {"file": ("test_image.jpg", f, "image/jpeg")}
        response = client.post(
            "/api/v0/media/upload", 
            files=files,
            headers=auth_headers
        )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "url" in response.json()
    assert duration < 0.005  # Less than 5ms


def test_delete_media(client, auth_headers):
    """Test deleting media from storage."""
    # Arrange
    media_path = "uploads/test_image.jpg"
    
    # Act
    start_time = time.time()
    response = client.delete(
        f"/api/v0/media/delete?path={media_path}",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.003  # Less than 3ms


@patch('app.db.supabase.client')
def test_create_post_database_error(mock_db_client, client, auth_headers, post_data):
    """Test handling of database errors when creating a post."""
    # Arrange
    mock_db_client.from_().insert().execute.side_effect = Exception("Database connection error")
    
    # Act
    response = client.post(
        "/api/v0/posts/", 
        json=post_data,
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "database" in response.json()["detail"].lower() 