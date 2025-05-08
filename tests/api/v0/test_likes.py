import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from uuid import UUID, uuid4
from app.main import app
from app.schemas.likes import LikeCreate

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

@pytest.fixture
def test_post(auth_headers):
    """Fixture to create a test post"""
    post_data = {
        "content": "Test post for likes",
        "media_urls": [],
        "location": "Test Location",
        "is_private": False
    }
    response = client.post(
        "/api/v0/posts/",
        headers=auth_headers,
        json=post_data
    )
    return response.json()

@pytest.fixture
def test_comment(auth_headers, test_post):
    """Fixture to create a test comment"""
    comment_data = {
        "content": "Test comment for likes",
        "post_id": test_post["id"]
    }
    response = client.post(
        "/api/v0/comments/",
        headers=auth_headers,
        json=comment_data
    )
    return response.json()

def test_like_post_success(auth_headers):
    """Test successful like of a post"""
    # First get a post ID from Alice's posts
    posts_response = client.get(
        "/api/v0/posts/user/alice",  # Using sample data username
        headers=auth_headers
    )
    post_id = posts_response.json()[0]["id"]
    
    response = client.post(
        f"/api/v0/likes/posts/{post_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data

def test_like_post_unauthorized():
    """Test like post without authentication"""
    response = client.post(
        f"/api/v0/likes/posts/{uuid4()}",
    )
    assert response.status_code == 401

def test_like_post_not_found(auth_headers):
    """Test like non-existent post"""
    non_existent_id = str(uuid4())
    response = client.post(
        f"/api/v0/likes/posts/{non_existent_id}",
        headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found"

def test_unlike_post_success(auth_headers):
    """Test successful unlike of a post"""
    # First get a post ID from Alice's posts
    posts_response = client.get(
        "/api/v0/posts/user/alice",  # Using sample data username
        headers=auth_headers
    )
    post_id = posts_response.json()[0]["id"]
    
    # First like the post
    client.post(
        f"/api/v0/likes/posts/{post_id}",
        headers=auth_headers
    )
    
    # Then unlike it
    response = client.delete(
        f"/api/v0/likes/posts/{post_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data

def test_unlike_post_unauthorized():
    """Test unlike post without authentication"""
    response = client.delete(
        f"/api/v0/likes/posts/{uuid4()}",
    )
    assert response.status_code == 401

def test_unlike_post_not_found(auth_headers):
    """Test unlike non-existent post"""
    non_existent_id = str(uuid4())
    response = client.delete(
        f"/api/v0/likes/posts/{non_existent_id}",
        headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found"

def test_get_post_likes_success(auth_headers):
    """Test successful retrieval of post likes"""
    # First get a post ID from Alice's posts
    posts_response = client.get(
        "/api/v0/posts/user/alice",  # Using sample data username
        headers=auth_headers
    )
    post_id = posts_response.json()[0]["id"]
    
    response = client.get(
        f"/api/v0/likes/posts/{post_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "id" in data[0]
        assert "user_id" in data[0]
        assert "post_id" in data[0]
        assert "created_at" in data[0]

def test_get_post_likes_unauthorized():
    """Test get post likes without authentication"""
    response = client.get(
        f"/api/v0/likes/posts/{uuid4()}",
    )
    assert response.status_code == 401

def test_get_post_likes_not_found(auth_headers):
    """Test get likes for non-existent post"""
    non_existent_id = str(uuid4())
    response = client.get(
        f"/api/v0/likes/posts/{non_existent_id}",
        headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found"

def test_get_user_liked_posts_success(auth_headers):
    """Test successful retrieval of user's liked posts"""
    response = client.get(
        "/api/v0/likes/user/posts",
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

def test_get_user_liked_posts_unauthorized():
    """Test get user's liked posts without authentication"""
    response = client.get("/api/v0/likes/user/posts")
    assert response.status_code == 401

def test_like_comment_success(auth_headers):
    """Test successful like of a comment"""
    # First get a post ID from Alice's posts
    posts_response = client.get(
        "/api/v0/posts/user/alice",  # Using sample data username
        headers=auth_headers
    )
    post_id = posts_response.json()[0]["id"]
    
    # Then get a comment ID from that post
    comments_response = client.get(
        f"/api/v0/posts/{post_id}/comments",
        headers=auth_headers
    )
    comment_id = comments_response.json()[0]["id"]
    
    response = client.post(
        f"/api/v0/likes/comments/{comment_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data

def test_unlike_comment_success(auth_headers):
    """Test successful unlike of a comment"""
    # First get a post ID from Alice's posts
    posts_response = client.get(
        "/api/v0/posts/user/alice",  # Using sample data username
        headers=auth_headers
    )
    post_id = posts_response.json()[0]["id"]
    
    # Then get a comment ID from that post
    comments_response = client.get(
        f"/api/v0/posts/{post_id}/comments",
        headers=auth_headers
    )
    comment_id = comments_response.json()[0]["id"]
    
    # First like the comment
    client.post(
        f"/api/v0/likes/comments/{comment_id}",
        headers=auth_headers
    )
    
    # Then unlike it
    response = client.delete(
        f"/api/v0/likes/comments/{comment_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data

def test_get_comment_likes_success(auth_headers):
    """Test successful retrieval of comment likes"""
    # First get a post ID from Alice's posts
    posts_response = client.get(
        "/api/v0/posts/user/alice",  # Using sample data username
        headers=auth_headers
    )
    post_id = posts_response.json()[0]["id"]
    
    # Then get a comment ID from that post
    comments_response = client.get(
        f"/api/v0/posts/{post_id}/comments",
        headers=auth_headers
    )
    comment_id = comments_response.json()[0]["id"]
    
    response = client.get(
        f"/api/v0/likes/comments/{comment_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "id" in data[0]
        assert "user_id" in data[0]
        assert "comment_id" in data[0]
        assert "created_at" in data[0]

def test_get_user_liked_comments_success(auth_headers):
    """Test successful retrieval of user's liked comments"""
    response = client.get(
        "/api/v0/likes/user/comments",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "id" in data[0]
        assert "content" in data[0]
        assert "user_id" in data[0]
        assert "post_id" in data[0]
        assert "created_at" in data[0] 