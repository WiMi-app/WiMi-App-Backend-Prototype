import pytest
import time
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import status


@pytest.fixture
def challenge_data():
    """Challenge creation data fixture."""
    return {
        "title": "Test Challenge",
        "description": "This is a test challenge",
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "location": "Test Location",
        "restriction": "No restrictions",
        "repetition": "daily",
        "repetition_frequency": 1,
        "repetition_days": [1, 3, 5],
        "check_in_time": "09:00:00",
        "is_private": False,
        "time_window": 60  # 60 minutes window for posting
    }


@pytest.fixture
def test_challenge(supabase_mock):
    """Create a test challenge fixture."""
    challenge_id = str(uuid4())
    user_id = supabase_mock.test_users[0]["id"]
    
    challenge = {
        "id": challenge_id,
        "creator_id": user_id,
        "title": "Existing Test Challenge",
        "description": "This is an existing test challenge",
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "location": "Test Location",
        "restriction": "No restrictions",
        "repetition": "daily",
        "repetition_frequency": 1,
        "repetition_days": [1, 3, 5],
        "check_in_time": "09:00:00",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "is_private": False,
        "time_window": 60
    }
    
    supabase_mock.tables["challenges"].data.append(challenge)
    return challenge


def test_create_challenge(client, auth_headers, challenge_data):
    """Test creating a new challenge."""
    # Act
    start_time = time.time()
    response = client.post(
        "/api/v0/challenges/", 
        json=challenge_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "id" in response.json()
    assert response.json()["title"] == challenge_data["title"]
    assert response.json()["description"] == challenge_data["description"]
    assert duration < 0.005  # Less than 5ms


def test_get_challenges(client, test_challenge):
    """Test getting a list of challenges."""
    # Act
    start_time = time.time()
    response = client.get("/api/v0/challenges/")
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0
    assert response.json()[0]["id"] == test_challenge["id"]
    assert response.json()[0]["title"] == test_challenge["title"]
    assert duration < 0.005  # Less than 5ms


def test_get_challenge_by_id(client, test_challenge):
    """Test getting a specific challenge by ID."""
    # Act
    start_time = time.time()
    response = client.get(f"/api/v0/challenges/{test_challenge['id']}")
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == test_challenge["id"]
    assert response.json()["title"] == test_challenge["title"]
    assert duration < 0.005  # Less than 5ms


def test_get_challenge_not_found(client):
    """Test getting a non-existent challenge returns 404."""
    # Act
    response = client.get(f"/api/v0/challenges/{uuid4()}")
    
    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_challenge(client, auth_headers, test_challenge):
    """Test updating a challenge."""
    # Arrange
    update_data = {
        "title": "Updated Challenge Title",
        "description": "Updated challenge description"
    }
    
    # Act
    start_time = time.time()
    response = client.put(
        f"/api/v0/challenges/{test_challenge['id']}", 
        json=update_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == test_challenge["id"]
    assert response.json()["title"] == update_data["title"]
    assert response.json()["description"] == update_data["description"]
    assert duration < 0.005  # Less than 5ms


def test_delete_challenge(client, auth_headers, test_challenge, supabase_mock):
    """Test deleting a challenge."""
    # Act
    start_time = time.time()
    response = client.delete(
        f"/api/v0/challenges/{test_challenge['id']}",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.005  # Less than 5ms
    
    # Verify challenge was deleted from mock DB
    challenges = [c for c in supabase_mock.tables["challenges"].data if c["id"] == test_challenge["id"]]
    assert len(challenges) == 0


def test_join_challenge(client, auth_headers, test_challenge, supabase_mock):
    """Test joining a challenge."""
    # Act
    start_time = time.time()
    response = client.post(
        f"/api/v0/challenges/{test_challenge['id']}/join",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.005  # Less than 5ms
    
    # Verify participation record was created
    participants = supabase_mock.tables["challenge_participants"].data
    assert len(participants) > 0
    assert participants[0]["challenge_id"] == test_challenge["id"]
    assert participants[0]["status"] == "active"


def test_leave_challenge(client, auth_headers, test_challenge, supabase_mock):
    """Test leaving a challenge."""
    # Arrange - add participation record
    user_id = supabase_mock.test_users[0]["id"]
    supabase_mock.tables["challenge_participants"].data.append({
        "challenge_id": test_challenge["id"],
        "user_id": user_id,
        "joined_at": datetime.now().isoformat() - timedelta(hours=1), # 1 hour ago
        "status": "active"
    })
    
    # Act
    start_time = time.time()
    response = client.post(
        f"/api/v0/challenges/{test_challenge['id']}/leave",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.005  # Less than 5ms
    
    # Verify status was updated
    participants = [p for p in supabase_mock.tables["challenge_participants"].data 
                    if p["challenge_id"] == test_challenge["id"] and p["user_id"] == user_id]
    assert len(participants) == 1
    assert participants[0]["status"] == "dropped"


def test_get_challenge_participants(client, test_challenge, supabase_mock):
    """Test getting challenge participants."""
    # Arrange - add participation records
    user_id1 = supabase_mock.test_users[0]["id"]
    user_id2 = str(uuid4())
    
    # Add another user
    supabase_mock.tables["users"].data.append({
        "id": user_id2,
        "username": "testuser2",
        "email": "test2@example.com",
        "created_at": datetime.now().isoformat()
    })
    
    supabase_mock.tables["challenge_participants"].data.extend([
        {
            "challenge_id": test_challenge["id"],
            "user_id": user_id1,
            "joined_at": datetime.now().isoformat() - timedelta(hours=1), # 1 hour ago
            "status": "active"
        },
        {
            "challenge_id": test_challenge["id"],
            "user_id": user_id2,
            "joined_at": datetime.now().isoformat() - timedelta(hours=2), # 2 hours ago
            "status": "active"
        }
    ])
    
    # Act
    start_time = time.time()
    response = client.get(f"/api/v0/challenges/{test_challenge['id']}/participants")
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) == 2
    assert duration < 0.005  # Less than 5ms


def test_create_challenge_post(client, auth_headers, test_challenge, supabase_mock):
    """Test creating a post for a challenge."""
    # Arrange
    post_data = {
        "content": "This is a challenge post",
        "challenge_id": test_challenge["id"],
        "media_urls": ["https://example.com/challenge_image.jpg"]
    }
    
    # Mock joining the challenge
    user_id = supabase_mock.test_users[0]["id"]
    supabase_mock.tables["challenge_participants"].data.append({
        "challenge_id": test_challenge["id"],
        "user_id": user_id,
        "joined_at": datetime.now().isoformat() - timedelta(hours=1), # 1 hour ago
        "status": "active"
    })
    
    # Act
    start_time = time.time()
    response = client.post(
        "/api/v0/challenges/posts", 
        json=post_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "id" in response.json()
    assert response.json()["content"] == post_data["content"]
    assert duration < 0.005  # Less than 5ms
    
    # Verify challenge-post relationship was created
    challenge_posts = supabase_mock.tables["challenge_posts"].data
    assert len(challenge_posts) > 0
    assert challenge_posts[0]["challenge_id"] == test_challenge["id"]


def test_get_challenge_posts(client, test_challenge, supabase_mock):
    """Test getting posts for a challenge."""
    # Arrange - create a post for the challenge
    post_id = str(uuid4())
    user_id = supabase_mock.test_users[0]["id"]
    
    supabase_mock.tables["posts"].data.append({
        "id": post_id,
        "user_id": user_id,
        "content": "Test challenge post",
        "created_at": datetime.now().isoformat() - timedelta(hours=1) # 1 hour ago
    })
    
    supabase_mock.tables["challenge_posts"].data.append({
        "challenge_id": test_challenge["id"],
        "post_id": post_id,
        "created_at": datetime.now().isoformat()
    })
    
    # Act
    start_time = time.time()
    response = client.get(f"/api/v0/challenges/{test_challenge['id']}/posts")
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0
    assert response.json()[0]["id"] == post_id
    assert duration < 0.005  # Less than 5ms


def test_challenge_achievement(client, auth_headers, test_challenge, supabase_mock):
    """Test creating a challenge achievement."""
    # Arrange
    user_id = supabase_mock.test_users[0]["id"]
    achievement_data = {
        "challenge_id": test_challenge["id"],
        "user_id": user_id,
        "achievement_type": "completion",
        "description": "Completed the challenge",
        "success_count": 10
    }
    
    # Act
    start_time = time.time()
    response = client.post(
        "/api/v0/challenges/achievements", 
        json=achievement_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "id" in response.json()
    assert response.json()["challenge_id"] == test_challenge["id"]
    assert response.json()["achievement_type"] == achievement_data["achievement_type"]
    assert duration < 0.005  # Less than 5ms


def test_update_challenge_forbidden(client, auth_headers, supabase_mock):
    """Test updating a challenge created by a different user."""
    # Arrange - create a challenge with a different creator
    challenge_id = str(uuid4())
    different_user_id = str(uuid4())
    
    # Add another user
    supabase_mock.tables["users"].data.append({
        "id": different_user_id,
        "username": "otheruser",
        "email": "other@example.com",
        "created_at": datetime.now().isoformat()
    })
    
    # Create challenge owned by different user
    challenge = {
        "id": challenge_id,
        "creator_id": different_user_id,
        "title": "Other User's Challenge",
        "description": "This challenge belongs to another user",
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "is_private": False
    }
    
    supabase_mock.tables["challenges"].data.append(challenge)
    
    # Act - try to update with current user's auth
    update_data = {
        "title": "Trying to update someone else's challenge",
        "description": "This should fail with a forbidden error"
    }
    
    response = client.put(
        f"/api/v0/challenges/{challenge_id}", 
        json=update_data,
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "permission" in response.json()["detail"].lower() or "not authorized" in response.json()["detail"].lower() 