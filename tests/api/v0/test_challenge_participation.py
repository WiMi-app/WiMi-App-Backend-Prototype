"""
Tests for challenge participation endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from tests.utils.auth import get_test_token

from app.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers fixture"""
    token = get_test_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_challenge_id(client, auth_headers):
    """Create a test challenge and return its ID"""
    challenge_data = {
        "title": "Test Challenge",
        "description": "Test challenge for participation endpoints"
    }
    
    response = client.post("/api/v0/challenges/", json=challenge_data, headers=auth_headers)
    assert response.status_code == 201
    
    return response.json()["id"]


def test_join_challenge(client, auth_headers, test_challenge_id):
    """Test joining a challenge"""
    # Join challenge
    response = client.post(f"/api/v0/challenges/{test_challenge_id}/join", headers=auth_headers)
    assert response.status_code == 201
    
    # Verify response data
    data = response.json()
    assert data["challenge_id"] == test_challenge_id
    assert "user_id" in data
    assert data["status"] == "active"
    
    # Try joining again - should fail
    response = client.post(f"/api/v0/challenges/{test_challenge_id}/join", headers=auth_headers)
    assert response.status_code == 400


def test_list_participants(client, auth_headers, test_challenge_id):
    """Test listing challenge participants"""
    # Join challenge first
    client.post(f"/api/v0/challenges/{test_challenge_id}/join", headers=auth_headers)
    
    # List participants
    response = client.get(f"/api/v0/challenges/{test_challenge_id}/participants", headers=auth_headers)
    assert response.status_code == 200
    
    # Verify response data
    data = response.json()
    assert len(data) >= 1
    assert data[0]["challenge_id"] == test_challenge_id


def test_update_status(client, auth_headers, test_challenge_id):
    """Test updating participation status"""
    # Join challenge first
    client.post(f"/api/v0/challenges/{test_challenge_id}/join", headers=auth_headers)
    
    # Update status
    response = client.put(
        f"/api/v0/challenges/{test_challenge_id}/status",
        params={"status": "completed"},
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Verify response data
    data = response.json()
    assert data["status"] == "completed"


def test_leave_challenge(client, auth_headers, test_challenge_id):
    """Test leaving a challenge"""
    # Join challenge first
    client.post(f"/api/v0/challenges/{test_challenge_id}/join", headers=auth_headers)
    
    # Leave challenge
    response = client.delete(f"/api/v0/challenges/{test_challenge_id}/leave", headers=auth_headers)
    assert response.status_code == 204
    
    # Try leaving again - should fail
    response = client.delete(f"/api/v0/challenges/{test_challenge_id}/leave", headers=auth_headers)
    assert response.status_code == 404


def test_get_participating_challenges(client, auth_headers, test_challenge_id):
    """Test getting challenges the user is participating in"""
    # Join challenge first
    client.post(f"/api/v0/challenges/{test_challenge_id}/join", headers=auth_headers)
    
    # Get participating challenges
    response = client.get("/api/v0/challenges/my/participating", headers=auth_headers)
    assert response.status_code == 200
    
    # Verify response data
    data = response.json()
    challenge_ids = [c["id"] for c in data]
    assert test_challenge_id in challenge_ids


def test_get_created_challenges(client, auth_headers, test_challenge_id):
    """Test getting challenges created by the user"""
    # Get created challenges
    response = client.get("/api/v0/challenges/my/created", headers=auth_headers)
    assert response.status_code == 200
    
    # Verify response data
    data = response.json()
    challenge_ids = [c["id"] for c in data]
    assert test_challenge_id in challenge_ids 