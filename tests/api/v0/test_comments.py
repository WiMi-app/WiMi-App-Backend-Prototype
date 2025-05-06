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
        "content": "Test post for comments",
        "media_urls": [],
        "created_at": datetime.now().isoformat() - timedelta(hours=2), # 2 hours ago
        "updated_at": datetime.now().isoformat() - timedelta(hours=1), # 1 hour ago
        "edited": False
    }
    
    supabase_mock.tables["posts"].data.append(post)
    return post


@pytest.fixture
def comment_data(test_post):
    return {
        "post_id": test_post["id"],
        "content": "This is a test comment",
        "parent_comment_id": None
    }


@pytest.fixture
def test_comment(supabase_mock, test_post):
    """Create a test comment fixture."""
    comment_id = str(uuid4())
    user_id = supabase_mock.test_users[0]["id"]
    
    comment = {
        "id": comment_id,
        "post_id": test_post["id"],
        "user_id": user_id,
        "content": "Existing test comment",
        "parent_comment_id": None,
        "created_at": "2023-01-01T00:00:00"
    }
    
    supabase_mock.tables["comments"].data.append(comment)
    return comment


def test_create_comment(client, auth_headers, comment_data):
    """Test creating a new comment."""
    # Act
    start_time = time.time()
    response = client.post(
        "/api/v0/comments/", 
        json=comment_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "id" in response.json()
    assert response.json()["content"] == comment_data["content"]
    assert response.json()["post_id"] == str(comment_data["post_id"])
    assert duration < 0.002  # Less than 2ms


def test_create_nested_comment(client, auth_headers, test_comment, test_post):
    """Test creating a nested reply to a comment."""
    # Arrange
    reply_data = {
        "post_id": test_post["id"],
        "content": "This is a nested reply",
        "parent_comment_id": test_comment["id"]
    }
    
    # Act
    start_time = time.time()
    response = client.post(
        "/api/v0/comments/", 
        json=reply_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "id" in response.json()
    assert response.json()["content"] == reply_data["content"]
    assert response.json()["parent_comment_id"] == str(reply_data["parent_comment_id"])
    assert duration < 0.002  # Less than 2ms


def test_get_comments_for_post(client, test_post, test_comment):
    """Test getting all comments for a post."""
    # Act
    start_time = time.time()
    response = client.get(f"/api/v0/comments/post/{test_post['id']}")
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0
    assert response.json()[0]["post_id"] == test_post["id"]
    assert duration < 0.005  # Less than 5ms


def test_get_comment(client, test_comment):
    """Test getting a specific comment by ID."""
    # Act
    start_time = time.time()
    response = client.get(f"/api/v0/comments/{test_comment['id']}")
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == test_comment["id"]
    assert response.json()["content"] == test_comment["content"]
    assert duration < 0.002  # Less than 2ms


def test_get_comment_not_found(client):
    """Test getting a non-existent comment returns 404."""
    # Act
    response = client.get(f"/api/v0/comments/{uuid4()}")
    
    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_comment(client, auth_headers, test_comment):
    """Test updating a comment."""
    # Arrange
    update_data = {
        "content": "Updated comment content"
    }
    
    # Act
    start_time = time.time()
    response = client.put(
        f"/api/v0/comments/{test_comment['id']}", 
        json=update_data,
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == test_comment["id"]
    assert response.json()["content"] == update_data["content"]
    assert duration < 0.002  # Less than 2ms


def test_delete_comment(client, auth_headers, test_comment, supabase_mock):
    """Test deleting a comment."""
    # Act
    start_time = time.time()
    response = client.delete(
        f"/api/v0/comments/{test_comment['id']}",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.002  # Less than 2ms
    
    # Verify comment was deleted from mock DB
    comments = [c for c in supabase_mock.tables["comments"].data if c["id"] == test_comment["id"]]
    assert len(comments) == 0


def test_delete_comment_with_replies(client, auth_headers, test_comment, supabase_mock):
    """Test deleting a comment that has replies."""
    # Arrange - add a reply to the comment
    reply_id = str(uuid4())
    user_id = supabase_mock.test_users[0]["id"]
    reply = {
        "id": reply_id,
        "post_id": test_comment["post_id"],
        "user_id": user_id,
        "content": "Reply to be cascaded",
        "parent_comment_id": test_comment["id"],
        "created_at": datetime.now().isoformat() - timedelta(hours=1) # 1 hour ago
    }
    supabase_mock.tables["comments"].data.append(reply)
    
    # Act
    start_time = time.time()
    response = client.delete(
        f"/api/v0/comments/{test_comment['id']}",
        headers=auth_headers
    )
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert duration < 0.002  # Less than 2ms
    
    # Verify both comment and reply were deleted
    comments = [c for c in supabase_mock.tables["comments"].data if c["id"] == test_comment["id"]]
    replies = [c for c in supabase_mock.tables["comments"].data if c["id"] == reply_id]
    assert len(comments) == 0
    assert len(replies) == 0


def test_table_relations(client, auth_headers, test_post, supabase_mock):
    """Test that comment table relations follow the schema."""
    # Arrange
    comment_data = {
        "post_id": test_post["id"],
        "content": "Test comment for relations"
    }
    
    # Act - create a comment
    response = client.post(
        "/api/v0/comments/", 
        json=comment_data,
        headers=auth_headers
    )
    
    # Assert comment created successfully
    assert response.status_code == status.HTTP_200_OK
    comment_id = response.json()["id"]
    
    # Act - delete the post
    client.delete(
        f"/api/v0/posts/{test_post['id']}",
        headers=auth_headers
    )
    
    # Assert comment was cascade deleted with the post
    comments = [c for c in supabase_mock.tables["comments"].data if c["id"] == comment_id]
    assert len(comments) == 0 