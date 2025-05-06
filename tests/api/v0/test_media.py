import pytest
import os
import time
from unittest.mock import patch, MagicMock
from fastapi import status


@pytest.fixture
def mock_image_file():
    """Create a temporary test image file."""
    file_path = "tests/test_files/test_image.jpg"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "wb") as f:
        f.write(b"test image content")
    
    yield file_path
    
    # Cleanup after test
    if os.path.exists(file_path):
        os.remove(file_path)


def test_upload_media(client, auth_headers, mock_image_file):
    """Test uploading media."""
    # Act
    start_time = time.time()
    with open(mock_image_file, "rb") as f:
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


def test_upload_profile_picture(client, auth_headers, mock_image_file):
    """Test uploading profile picture."""
    # Act
    start_time = time.time()
    with open(mock_image_file, "rb") as f:
        files = {"file": ("profile.jpg", f, "image/jpeg")}
        response = client.post(
            "/api/v0/media/upload/profile",
            files=files,
            headers=auth_headers
        )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "url" in response.json()
    assert "profile" in response.json()["url"]
    assert duration < 0.005  # Less than 5ms


def test_upload_media_invalid_file(client, auth_headers):
    """Test uploading invalid media file type."""
    # Create an invalid file type
    file_path = "tests/test_files/test_invalid.txt"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "w") as f:
        f.write("This is not an image or video")
    
    # Act
    with open(file_path, "rb") as f:
        files = {"file": ("test_invalid.txt", f, "text/plain")}
        response = client.post(
            "/api/v0/media/upload",
            files=files,
            headers=auth_headers
        )
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid file type" in response.json()["detail"]


def test_upload_media_large_file(client, auth_headers):
    """Test uploading a file that exceeds size limits."""
    # Create a large file
    file_path = "tests/test_files/large_test_image.jpg"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create a file just over 6MB
    with open(file_path, "wb") as f:
        f.write(b"0" * (6 * 1024 * 1024 + 1))
    
    # Act
    with open(file_path, "rb") as f:
        files = {"file": ("large_test_image.jpg", f, "image/jpeg")}
        response = client.post(
            "/api/v0/media/upload",
            files=files,
            headers=auth_headers
        )
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "File too large" in response.json()["detail"]


def test_delete_media(client, auth_headers):
    """Test deleting media."""
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


def test_delete_profile_picture(client, auth_headers, supabase_mock):
    """Test deleting a profile picture."""
    # Arrange - set user avatar URL
    user_id = supabase_mock.test_users[0]["id"]
    avatar_url = "https://example.com/profile/user1.jpg"
    
    for i, user in enumerate(supabase_mock.tables["users"].data):
        if user["id"] == user_id:
            supabase_mock.tables["users"].data[i]["avatar_url"] = avatar_url
    
    # Act
    start_time = time.time()
    response = client.delete(
        "/api/v0/media/profile",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.003  # Less than 3ms
    
    # Verify avatar URL was removed
    user = next(u for u in supabase_mock.tables["users"].data if u["id"] == user_id)
    assert user["avatar_url"] is None


@patch('app.api.v0.media.process_image')
def test_optimize_media(mock_process_image, client, auth_headers, mock_image_file):
    """Test optimizing media."""
    # Arrange
    mock_process_image.return_value = b"optimized image content"
    
    # Act
    start_time = time.time()
    with open(mock_image_file, "rb") as f:
        files = {"file": ("test_image.jpg", f, "image/jpeg")}
        response = client.post(
            "/api/v0/media/optimize",
            files=files,
            headers=auth_headers
        )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "url" in response.json()
    assert duration < 0.005  # Less than 5ms
    assert mock_process_image.called


def test_get_media_metadata(client, auth_headers):
    """Test getting metadata for media."""
    # Arrange
    media_url = "https://example.com/uploads/test_image.jpg"
    
    # Act
    start_time = time.time()
    response = client.get(
        f"/api/v0/media/metadata?url={media_url}",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "type" in response.json()
    assert "size" in response.json()
    assert "dimensions" in response.json()
    assert duration < 0.005  # Less than 5ms


def test_update_media_permissions(client, auth_headers):
    """Test updating media permissions."""
    # Arrange
    media_path = "uploads/test_image.jpg"
    permissions_data = {
        "path": media_path,
        "is_public": True
    }
    
    # Act
    start_time = time.time()
    response = client.put(
        "/api/v0/media/permissions",
        json=permissions_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.005  # Less than 5ms
    
    
def test_load_media(client):
    """Test loading media."""
    # Arrange
    media_url = "https://example.com/media/test_image.jpg"
    
    # Act
    start_time = time.time()
    response = client.get(
        f"/api/v0/media/load?url={media_url}"
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert duration < 0.005  # Less than 5ms 