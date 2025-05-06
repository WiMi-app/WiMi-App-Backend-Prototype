import pytest
import time
from uuid import uuid4
from fastapi import status
from datetime import datetime, timedelta

@pytest.fixture
def test_post(supabase_mock):
    """Create a test post fixture."""
    post_id = str(uuid4())
    user_id = supabase_mock.test_users[0]["id"]
    
    post = {
        "id": post_id,
        "user_id": user_id,
        "content": "Test post for likes",
        "media_urls": [],
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00",
        "edited": False
    }
    
    supabase_mock.tables["posts"].data.append(post)
    return post


@pytest.fixture
def test_comment(supabase_mock, test_post):
    """Create a test comment fixture."""
    comment_id = str(uuid4())
    user_id = supabase_mock.test_users[0]["id"]
    
    comment = {
        "id": comment_id,
        "post_id": test_post["id"],
        "user_id": user_id,
        "content": "Test comment for likes",
        "parent_comment_id": None,
        "created_at": datetime.now().isoformat()
    }
    
    supabase_mock.tables["comments"].data.append(comment)
    return comment


def test_like_post(client, auth_headers, test_post, supabase_mock):
    """Test liking a post."""
    # Arrange
    like_data = {
        "post_id": test_post["id"]
    }
    
    # Act
    start_time = time.time()
    response = client.post(
        "/api/v0/likes/", 
        json=like_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "id" in response.json()
    assert response.json()["post_id"] == test_post["id"]
    assert duration < 0.005  # Less than 5ms
    
    # Verify like was created in mock DB
    likes = [l for l in supabase_mock.tables["likes"].data if l["post_id"] == test_post["id"]]
    assert len(likes) == 1


def test_like_comment(client, auth_headers, test_comment, supabase_mock):
    """Test liking a comment."""
    # Arrange
    like_data = {
        "comment_id": test_comment["id"]
    }
    
    # Act
    start_time = time.time()
    response = client.post(
        "/api/v0/likes/", 
        json=like_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "id" in response.json()
    assert response.json()["comment_id"] == test_comment["id"]
    assert duration < 0.005  # Less than 5ms
    
    # Verify like was created in mock DB
    likes = [l for l in supabase_mock.tables["likes"].data if l["comment_id"] == test_comment["id"]]
    assert len(likes) == 1


def test_like_post_already_liked(client, auth_headers, test_post, supabase_mock):
    """Test liking a post that's already liked returns an error."""
    # Arrange - create existing like
    user_id = supabase_mock.test_users[0]["id"]
    supabase_mock.tables["likes"].data.append({
        "id": str(uuid4()),
        "user_id": user_id,
        "post_id": test_post["id"],
        "created_at": datetime.now().isoformat() - timedelta(hours=1) # 1 hour ago
    })
    
    like_data = {
        "post_id": test_post["id"]
    }
    
    # Act
    response = client.post(
        "/api/v0/likes/", 
        json=like_data,
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Already liked" in response.json()["detail"]


def test_unlike_post(client, auth_headers, test_post, supabase_mock):
    """Test unliking a post."""
    # Arrange - create existing like
    like_id = str(uuid4())
    user_id = supabase_mock.test_users[0]["id"]
    supabase_mock.tables["likes"].data.append({
        "id": like_id,
        "user_id": user_id,
        "post_id": test_post["id"],
        "comment_id": None,
        "created_at": "2023-01-01T00:00:00"
    })
    
    # Act
    start_time = time.time()
    response = client.delete(
        f"/api/v0/likes/post/{test_post['id']}",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.005  # Less than 5ms
    
    # Verify like was removed
    likes = [l for l in supabase_mock.tables["likes"].data if l["id"] == like_id]
    assert len(likes) == 0


def test_unlike_comment(client, auth_headers, test_comment, supabase_mock):
    """Test unliking a comment."""
    # Arrange - create existing like
    like_id = str(uuid4())
    user_id = supabase_mock.test_users[0]["id"]
    supabase_mock.tables["likes"].data.append({
        "id": like_id,
        "user_id": user_id,
        "post_id": None,
        "comment_id": test_comment["id"],
        "created_at": "2023-01-01T00:00:00"
    })
    
    # Act
    start_time = time.time()
    response = client.delete(
        f"/api/v0/likes/comment/{test_comment['id']}",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.005  # Less than 5ms
    
    # Verify like was removed
    likes = [l for l in supabase_mock.tables["likes"].data if l["id"] == like_id]
    assert len(likes) == 0


def test_get_post_likes(client, test_post, supabase_mock):
    """Test getting likes for a post."""
    # Arrange - create some likes
    user_id1 = supabase_mock.test_users[0]["id"]
    user_id2 = str(uuid4())
    
    # Add another user
    supabase_mock.tables["users"].data.append({
        "id": user_id2,
        "username": "testuser2",
        "email": "test2@example.com"
    })
    
    supabase_mock.tables["likes"].data.extend([
        {
            "id": str(uuid4()),
            "user_id": user_id1,
            "post_id": test_post["id"],
            "comment_id": None,
            "created_at": "2023-01-01T00:00:00"
        },
        {
            "id": str(uuid4()),
            "user_id": user_id2,
            "post_id": test_post["id"],
            "comment_id": None,
            "created_at": "2023-01-01T00:00:00"
        }
    ])
    
    # Act
    start_time = time.time()
    response = client.get(f"/api/v0/likes/post/{test_post['id']}")
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) == 2
    assert duration < 0.005  # Less than 5ms


def test_get_comment_likes(client, test_comment, supabase_mock):
    """Test getting likes for a comment."""
    # Arrange - create a like
    user_id = supabase_mock.test_users[0]["id"]
    supabase_mock.tables["likes"].data.append({
        "id": str(uuid4()),
        "user_id": user_id,
        "post_id": None,
        "comment_id": test_comment["id"],
        "created_at": "2023-01-01T00:00:00"
    })
    
    # Act
    start_time = time.time()
    response = client.get(f"/api/v0/likes/comment/{test_comment['id']}")
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    assert duration < 0.005  # Less than 5ms


def test_check_if_user_liked_post(client, auth_headers, test_post, supabase_mock):
    """Test checking if a user has liked a post."""
    # Arrange - create a like
    user_id = supabase_mock.test_users[0]["id"]
    supabase_mock.tables["likes"].data.append({
        "id": str(uuid4()),
        "user_id": user_id,
        "post_id": test_post["id"],
        "comment_id": None,
        "created_at": "2023-01-01T00:00:00"
    })
    
    # Act
    start_time = time.time()
    response = client.get(
        f"/api/v0/likes/check/post/{test_post['id']}",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["liked"] is True
    assert duration < 0.005  # Less than 5ms


def test_check_if_user_liked_comment(client, auth_headers, test_comment, supabase_mock):
    """Test checking if a user has liked a comment."""
    # Act - without creating a like
    start_time = time.time()
    response = client.get(
        f"/api/v0/likes/check/comment/{test_comment['id']}",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["liked"] is False
    assert duration < 0.005  # Less than 5ms 