import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from uuid import UUID, uuid4
from app.main import app

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

def test_moderation_test_success(auth_headers):
    """Test successful moderation test"""
    test_data = {
        "text_content": "Just finished my morning run!",  # Using sample post content
        "image_urls": ["post_media/alice_run1.jpg"]  # Using sample media URL
    }
    response = client.post(
        "/api/v0/moderation/test",
        headers=auth_headers,
        json=test_data
    )
    assert response.status_code == 200
    data = response.json()
    assert "flagged" in data
    assert "categories" in data
    assert "category_scores" in data
    assert "timestamp" in data

def test_moderation_test_missing_content(auth_headers):
    """Test moderation test with missing content"""
    test_data = {}
    response = client.post(
        "/api/v0/moderation/test",
        headers=auth_headers,
        json=test_data
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "At least one of text_content or image_urls must be provided"

def test_moderation_test_unauthorized():
    """Test moderation test without authentication"""
    test_data = {
        "text_content": "Starting my reading challenge tonight."  # Using sample post content
    }
    response = client.post(
        "/api/v0/moderation/test",
        json=test_data
    )
    assert response.status_code == 401

def test_safe_content_check_success(auth_headers):
    """Test successful safe content check"""
    test_data = {
        "text_content": "Morning yoga done!",  # Using sample post content
        "image_urls": ["post_media/carol_yoga.jpg"]  # Using sample media URL
    }
    response = client.post(
        "/api/v0/moderation/safe-check",
        headers=auth_headers,
        json=test_data
    )
    assert response.status_code == 200
    data = response.json()
    assert "is_safe" in data
    assert "timestamp" in data
    assert isinstance(data["is_safe"], bool)

def test_safe_content_check_missing_content(auth_headers):
    """Test safe content check with missing content"""
    test_data = {}
    response = client.post(
        "/api/v0/moderation/safe-check",
        headers=auth_headers,
        json=test_data
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "At least one of text_content or image_urls must be provided"

def test_safe_content_check_unauthorized():
    """Test safe content check without authentication"""
    test_data = {
        "text_content": "Pushed out 50 push-ups!"  # Using sample post content
    }
    response = client.post(
        "/api/v0/moderation/safe-check",
        json=test_data
    )
    assert response.status_code == 401

def test_public_moderation_test_success():
    """Test successful public moderation test"""
    test_data = {
        "text_content": "Great job, Alice!",  # Using sample comment content
        "image_urls": []
    }
    response = client.post(
        "/api/v0/moderation/public/test",
        json=test_data
    )
    assert response.status_code == 200
    data = response.json()
    assert "flagged" in data
    assert "categories" in data
    assert "timestamp" in data

def test_public_moderation_test_missing_content():
    """Test public moderation test with missing content"""
    test_data = {}
    response = client.post(
        "/api/v0/moderation/public/test",
        json=test_data
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "At least one of text_content or image_urls must be provided"

def test_public_safe_content_check_success():
    """Test successful public safe content check"""
    test_data = {
        "text_content": "Good luck, Bob!",  # Using sample comment content
        "image_urls": []
    }
    response = client.post(
        "/api/v0/moderation/public/safe-check",
        json=test_data
    )
    assert response.status_code == 200
    data = response.json()
    assert "is_safe" in data
    assert "timestamp" in data
    assert isinstance(data["is_safe"], bool)

def test_public_safe_content_check_missing_content():
    """Test public safe content check with missing content"""
    test_data = {}
    response = client.post(
        "/api/v0/moderation/public/safe-check",
        json=test_data
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "At least one of text_content or image_urls must be provided"

def test_moderation_with_flagged_content(auth_headers):
    """Test moderation with content that should be flagged"""
    test_data = {
        "text_content": "This is inappropriate content",
        "image_urls": ["post_media/inappropriate-image.jpg"]
    }
    response = client.post(
        "/api/v0/moderation/test",
        headers=auth_headers,
        json=test_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["flagged"] is True
    assert len(data["categories"]) > 0
    assert len(data["category_scores"]) > 0

def test_moderation_with_safe_content(auth_headers):
    """Test moderation with content that should be safe"""
    test_data = {
        "text_content": "Impressive flexibility!",  # Using sample comment content
        "image_urls": []
    }
    response = client.post(
        "/api/v0/moderation/test",
        headers=auth_headers,
        json=test_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["flagged"] is False
    assert len(data["categories"]) == 0
    assert len(data["category_scores"]) == 0

def test_moderation_with_invalid_image_url(auth_headers):
    """Test moderation with invalid image URL"""
    test_data = {
        "text_content": "Starting my reading challenge tonight.",  # Using sample post content
        "image_urls": ["not-a-valid-url"]
    }
    response = client.post(
        "/api/v0/moderation/test",
        headers=auth_headers,
        json=test_data
    )
    assert response.status_code == 200  # Should still process but flag the invalid URL
    data = response.json()
    assert "flagged" in data
    assert "categories" in data
    assert "category_scores" in data

def test_moderation_with_empty_text(auth_headers):
    """Test moderation with empty text content"""
    test_data = {
        "text_content": "",
        "image_urls": ["post_media/carol_yoga.jpg"]  # Using sample media URL
    }
    response = client.post(
        "/api/v0/moderation/test",
        headers=auth_headers,
        json=test_data
    )
    assert response.status_code == 200
    data = response.json()
    assert "flagged" in data
    assert "categories" in data
    assert "category_scores" in data

def test_moderation_with_long_text(auth_headers):
    """Test moderation with very long text content"""
    long_text = "Just finished my morning run! " * 1000  # Create a long text using sample content
    test_data = {
        "text_content": long_text,
        "image_urls": []
    }
    response = client.post(
        "/api/v0/moderation/test",
        headers=auth_headers,
        json=test_data
    )
    assert response.status_code == 200
    data = response.json()
    assert "flagged" in data
    assert "categories" in data
    assert "category_scores" in data 