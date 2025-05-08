import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from uuid import UUID, uuid4
from app.main import app
from app.recommendation.models import PostRecommendationRequest, ChallengeRecommendationRequest

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

def test_recommend_posts_success(auth_headers):
    """Test successful post recommendations"""
    request_data = {
        "user_id": str(uuid4()),
        "limit": 10,
        "exclude_seen": True,
        "categories": ["fitness", "education", "wellness", "strength"],  # Using sample challenge categories
        "min_engagement": 0.5
    }
    response = client.post(
        "/api/v0/recommendations/posts/recommend",
        headers=auth_headers,
        json=request_data
    )
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert "metadata" in data
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) <= request_data["limit"]
    # Verify recommendations based on sample data
    if len(data["recommendations"]) > 0:
        assert any("Morning Run" in rec.get("content", "") for rec in data["recommendations"])
        assert any("Read a Book" in rec.get("content", "") for rec in data["recommendations"])
        assert any("Yoga Stretch" in rec.get("content", "") for rec in data["recommendations"])
        assert any("Push-Up Challenge" in rec.get("content", "") for rec in data["recommendations"])

def test_recommend_posts_unauthorized():
    """Test post recommendations without authentication"""
    request_data = {
        "user_id": str(uuid4()),
        "limit": 10
    }
    response = client.post(
        "/api/v0/recommendations/posts/recommend",
        json=request_data
    )
    assert response.status_code == 401

def test_recommend_posts_invalid_data(auth_headers):
    """Test post recommendations with invalid data"""
    invalid_data = {
        "user_id": "not-a-uuid",
        "limit": -1,  # Invalid limit
        "exclude_seen": "not-a-boolean"  # Invalid boolean
    }
    response = client.post(
        "/api/v0/recommendations/posts/recommend",
        headers=auth_headers,
        json=invalid_data
    )
    assert response.status_code == 422  # Validation error

def test_recommend_posts_empty_categories(auth_headers):
    """Test post recommendations with empty categories"""
    request_data = {
        "user_id": str(uuid4()),
        "limit": 10,
        "categories": []
    }
    response = client.post(
        "/api/v0/recommendations/posts/recommend",
        headers=auth_headers,
        json=request_data
    )
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)

def test_recommend_posts_zero_limit(auth_headers):
    """Test post recommendations with zero limit"""
    request_data = {
        "user_id": str(uuid4()),
        "limit": 0
    }
    response = client.post(
        "/api/v0/recommendations/posts/recommend",
        headers=auth_headers,
        json=request_data
    )
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) == 0

def test_record_post_interaction_success(auth_headers):
    """Test successful post interaction recording"""
    # Using sample post content to find a post ID
    post_content = "Just finished my morning run!"
    response = client.get(
        "/api/v0/posts/",
        headers=auth_headers,
        params={"content": post_content}
    )
    assert response.status_code == 200
    posts = response.json()
    assert len(posts) > 0
    post_id = posts[0]["id"]
    
    interaction_type = "view"
    response = client.post(
        f"/api/v0/recommendations/posts/{post_id}/interactions/{interaction_type}",
        headers=auth_headers,
        json={"user_id": str(uuid4())}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data

def test_record_post_interaction_invalid_type(auth_headers):
    """Test post interaction recording with invalid type"""
    # Using sample post content to find a post ID
    post_content = "Starting my reading challenge tonight."
    response = client.get(
        "/api/v0/posts/",
        headers=auth_headers,
        params={"content": post_content}
    )
    assert response.status_code == 200
    posts = response.json()
    assert len(posts) > 0
    post_id = posts[0]["id"]
    
    invalid_type = "invalid_type"
    response = client.post(
        f"/api/v0/recommendations/posts/{post_id}/interactions/{invalid_type}",
        headers=auth_headers,
        json={"user_id": str(uuid4())}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid interaction type"

def test_record_post_interaction_unauthorized():
    """Test post interaction recording without authentication"""
    # Using sample post content to find a post ID
    post_content = "Morning yoga done!"
    response = client.get(
        "/api/v0/posts/",
        params={"content": post_content}
    )
    assert response.status_code == 401

def test_record_post_interaction_invalid_uuid(auth_headers):
    """Test post interaction recording with invalid UUID"""
    post_id = "not-a-uuid"
    interaction_type = "view"
    response = client.post(
        f"/api/v0/recommendations/posts/{post_id}/interactions/{interaction_type}",
        headers=auth_headers,
        json={"user_id": str(uuid4())}
    )
    assert response.status_code == 422  # Validation error

def test_record_post_interaction_missing_user_id(auth_headers):
    """Test post interaction recording without user ID"""
    # Using sample post content to find a post ID
    post_content = "Pushed out 50 push-ups!"
    response = client.get(
        "/api/v0/posts/",
        headers=auth_headers,
        params={"content": post_content}
    )
    assert response.status_code == 200
    posts = response.json()
    assert len(posts) > 0
    post_id = posts[0]["id"]
    
    interaction_type = "view"
    response = client.post(
        f"/api/v0/recommendations/posts/{post_id}/interactions/{interaction_type}",
        headers=auth_headers,
        json={}
    )
    assert response.status_code == 422  # Validation error

def test_record_post_interaction_all_types(auth_headers):
    """Test recording all valid interaction types"""
    # Using sample post content to find a post ID
    post_content = "Just finished my morning run!"
    response = client.get(
        "/api/v0/posts/",
        headers=auth_headers,
        params={"content": post_content}
    )
    assert response.status_code == 200
    posts = response.json()
    assert len(posts) > 0
    post_id = posts[0]["id"]
    
    valid_types = ["view", "like", "comment", "save", "share"]
    for interaction_type in valid_types:
        response = client.post(
            f"/api/v0/recommendations/posts/{post_id}/interactions/{interaction_type}",
            headers=auth_headers,
            json={"user_id": str(uuid4())}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data 