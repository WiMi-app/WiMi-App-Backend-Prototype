import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from uuid import UUID, uuid4
from app.main import app

client = TestClient(app)

@pytest.fixture
def admin_token():
    """Fixture to get admin authentication token"""
    response = client.post(
        "/api/v0/auth/login",
        data={
            "username": "admin@example.com",
            "password": "adminpassword123"
        }
    )
    return response.json()["access_token"]

@pytest.fixture
def admin_headers(admin_token):
    """Fixture to get admin authentication headers"""
    return {"Authorization": f"Bearer {admin_token}"}

@pytest.fixture
def regular_user_token():
    """Fixture to get regular user authentication token"""
    response = client.post(
        "/api/v0/auth/login",
        data={
            "username": "alice",  # Using sample data user
            "password": "testpassword123"
        }
    )
    return response.json()["access_token"]

@pytest.fixture
def regular_user_headers(regular_user_token):
    """Fixture to get regular user authentication headers"""
    return {"Authorization": f"Bearer {regular_user_token}"}

def test_get_moderation_stats_success(admin_headers):
    """Test successful retrieval of moderation statistics"""
    response = client.get(
        "/api/v0/admin/moderation/stats",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_checks" in data
    assert "flagged_content" in data
    assert "category_stats" in data
    assert "server_time" in data
    # Verify stats based on sample data
    assert data["total_checks"] >= 4  # At least 4 posts in sample data
    assert "fitness" in data["category_stats"]  # From Morning Run challenge
    assert "education" in data["category_stats"]  # From Read a Book challenge
    assert "wellness" in data["category_stats"]  # From Yoga Stretch challenge
    assert "strength" in data["category_stats"]  # From Push-Up Challenge

def test_get_moderation_stats_unauthorized():
    """Test retrieval of moderation statistics without authentication"""
    response = client.get("/api/v0/admin/moderation/stats")
    assert response.status_code == 401

def test_get_moderation_stats_non_admin(regular_user_headers):
    """Test retrieval of moderation statistics by non-admin user"""
    response = client.get(
        "/api/v0/admin/moderation/stats",
        headers=regular_user_headers
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access admin endpoints"

def test_test_moderation_success(admin_headers):
    """Test successful moderation test"""
    test_data = {
        "text_content": "Just finished my morning run!",  # Using sample post content
        "image_urls": ["post_media/alice_run1.jpg"]  # Using sample media URL
    }
    response = client.post(
        "/api/v0/admin/moderation/test",
        headers=admin_headers,
        json=test_data
    )
    assert response.status_code == 200
    data = response.json()
    assert "input" in data
    assert "moderation_result" in data
    assert "timestamp" in data
    assert data["input"]["text_content"] == test_data["text_content"]
    assert data["input"]["image_urls"] == test_data["image_urls"]

def test_test_moderation_unauthorized():
    """Test moderation test without authentication"""
    test_data = {
        "text_content": "Starting my reading challenge tonight."  # Using sample post content
    }
    response = client.post(
        "/api/v0/admin/moderation/test",
        json=test_data
    )
    assert response.status_code == 401

def test_test_moderation_non_admin(regular_user_headers):
    """Test moderation test by non-admin user"""
    test_data = {
        "text_content": "Morning yoga done!"  # Using sample post content
    }
    response = client.post(
        "/api/v0/admin/moderation/test",
        headers=regular_user_headers,
        json=test_data
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access admin endpoints"

def test_test_moderation_missing_content(admin_headers):
    """Test moderation test with missing content"""
    test_data = {}
    response = client.post(
        "/api/v0/admin/moderation/test",
        headers=admin_headers,
        json=test_data
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "At least one of text_content or image_urls must be provided"

def test_test_bulk_moderation_success(admin_headers):
    """Test successful bulk moderation test"""
    test_data = {
        "content_items": [
            {
                "text_content": "Just finished my morning run!",  # Alice's post
                "image_urls": ["post_media/alice_run1.jpg"]
            },
            {
                "text_content": "Starting my reading challenge tonight.",  # Bob's post
                "image_urls": []
            },
            {
                "text_content": "Morning yoga done!",  # Carol's post
                "image_urls": ["post_media/carol_yoga.jpg"]
            },
            {
                "text_content": "Pushed out 50 push-ups!",  # Dave's post
                "image_urls": ["post_media/dave_pushup.jpg"]
            }
        ]
    }
    response = client.post(
        "/api/v0/admin/moderation/test-bulk",
        headers=admin_headers,
        json=test_data
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(test_data["content_items"])
    for item in data:
        assert "input" in item
        assert "moderation_result" in item
        assert "timestamp" in item

def test_test_bulk_moderation_unauthorized():
    """Test bulk moderation test without authentication"""
    test_data = {
        "content_items": [
            {
                "text_content": "Great job, Alice!",  # Using sample comment content
                "image_urls": []
            }
        ]
    }
    response = client.post(
        "/api/v0/admin/moderation/test-bulk",
        json=test_data
    )
    assert response.status_code == 401

def test_test_bulk_moderation_non_admin(regular_user_headers):
    """Test bulk moderation test by non-admin user"""
    test_data = {
        "content_items": [
            {
                "text_content": "Impressive flexibility!",  # Using sample comment content
                "image_urls": []
            }
        ]
    }
    response = client.post(
        "/api/v0/admin/moderation/test-bulk",
        headers=regular_user_headers,
        json=test_data
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access admin endpoints"

def test_test_bulk_moderation_empty_list(admin_headers):
    """Test bulk moderation test with empty content list"""
    test_data = {
        "content_items": []
    }
    response = client.post(
        "/api/v0/admin/moderation/test-bulk",
        headers=admin_headers,
        json=test_data
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "The content_items list cannot be empty"

def test_test_bulk_moderation_invalid_data(admin_headers):
    """Test bulk moderation test with invalid data"""
    test_data = {
        "content_items": [
            {
                "text_content": 123,  # Invalid type
                "image_urls": "not-a-list"  # Invalid type
            }
        ]
    }
    response = client.post(
        "/api/v0/admin/moderation/test-bulk",
        headers=admin_headers,
        json=test_data
    )
    assert response.status_code == 422  # Validation error

def test_test_bulk_moderation_mixed_content(admin_headers):
    """Test bulk moderation test with mixed content types"""
    test_data = {
        "content_items": [
            {
                "text_content": "Starting my reading challenge tonight."  # Text only post
            },
            {
                "image_urls": ["post_media/carol_yoga.jpg"]  # Image only post
            },
            {
                "text_content": "Just finished my morning run!",  # Mixed content post
                "image_urls": ["post_media/alice_run1.jpg"]
            }
        ]
    }
    response = client.post(
        "/api/v0/admin/moderation/test-bulk",
        headers=admin_headers,
        json=test_data
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(test_data["content_items"]) 