import json
import uuid
from datetime import datetime, timedelta
from typing import Dict

import pytest
from fastapi.testclient import TestClient
from supabase import Client, create_client

from app.core.config import settings
from app.main import app

# Setup test client
client = TestClient(app)

# Setup Supabase client for test database
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)

BASE_ICON_URL = str(f"{settings.SUPABASE_URL}/storage/v1/object/sign/images/default/icon.png?token={settings.SUPABASE_KEY}")
BASE_COVER_IMAGE_URL = str(f"{settings.SUPABASE_URL}/storage/v1/object/sign/images/default/cover.png?token={settings.SUPABASE_KEY}")


# Image metadata is now optional, so we can just return an empty dict or None
def create_valid_image_metadata():
    """
    Returns None as image metadata is now optional.
    This function is kept for backward compatibility with existing tests.
    """
    return None


@pytest.fixture(scope="module")
def test_user():
    """
    Create a test user for challenge post testing.
    
    This fixture:
    1. Creates a test user with fixed credentials
    2. Registers the user via the auth API
    3. Logs in the user to obtain access token
    4. Yields the user data including token
    5. Cleans up by deleting the user after tests complete
    
    Returns:
        dict: User data including id, username, email, and auth token
    """
    username = "tester"
    email = f"wimi-{uuid.uuid4().hex[:8]}@test.com"
    password = "tester1"
    
    # Create user using the registration API instead of direct DB insert
    user_data = {
        "username": username,
        "email": email,
        "password": password,
        "full_name": "Test User",
        "bio": "Test bio",
    }
    
    register_response = client.post(
        "/api/v1/auth/register",
        json=user_data
    )
        
    if register_response.status_code != 200:
        pytest.fail(f"Failed to create test user: {register_response.json()}")
    
    user_id = register_response.json()["id"]
    
    # Login to get access token
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password}
    )
    
    if login_response.status_code != 200:
        pytest.fail("Failed to log in test user")
    
    token_data = login_response.json()
    
    yield {
        "id": user_id,
        "username": username,
        "email": email,
        "token": token_data["access_token"]
    }
    
    # Clean up: delete the test user
    supabase.table("users").delete().eq("id", user_id).execute()


@pytest.fixture(scope="module")
def test_challenge(test_user):
    """
    Create a test challenge for post testing.
    
    This fixture:
    1. Creates a challenge with a unique title
    2. Directly inserts the challenge into the database
    3. Yields challenge data for test use
    4. Cleans up by deleting the challenge after tests complete
    
    Args:
        test_user: Fixture providing creator credentials

    Returns:
        dict: Challenge data including id, title, and description
    """
    challenge_data = {
        "title": f"Test Challenge {uuid.uuid4().hex[:8]}",
        "description": "Test description for the challenge",
        "creator_id": test_user["id"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "is_active": True,
        "is_private": False,
    }
    
    result = supabase.table("challenges").insert(challenge_data).execute()
    
    if not result.data or len(result.data) == 0:
        pytest.fail("Failed to create test challenge")
    
    challenge_id = result.data[0]["id"]
    
    yield {
        "id": challenge_id,
        "title": challenge_data["title"],
        "description": challenge_data["description"],
    }
    
    # Clean up: delete the test challenge
    supabase.table("challenges").delete().eq("id", challenge_id).execute()


@pytest.fixture(scope="module")
def test_post(test_user):
    """
    Create a test post for challenge post testing.
    
    This fixture:
    1. Creates a post using the authenticated user
    2. Creates post via the API
    3. Yields post data for test use
    4. Cleans up by deleting the post after tests complete
    
    Args:
        test_user: Fixture providing authenticated user credentials

    Returns:
        dict: Post data including id and content
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # Create post using API instead of direct DB insert
    post_data = {
        "content": f"Test post content {uuid.uuid4().hex[:8]}",
        "media_urls": [BASE_ICON_URL],
        "is_private": False
    }
    
    # Create post
    response = client.post(
        "/api/v1/posts/",
        headers=headers,
        json=post_data
    )
    
    if response.status_code != 200:
        pytest.fail(f"Failed to create test post: {response.json()}")
    
    post = response.json()
    
    yield {
        "id": post["id"],
        "content": post["content"],
    }
    
    # Clean up: delete the test post
    supabase.table("posts").delete().eq("id", post["id"]).execute()


def test_add_post_to_challenge(test_user, test_challenge, test_post):
    """
    Test adding a post to a challenge.
    
    This test:
    1. Adds an existing post to a challenge
    2. Marks it as a check-in post
    3. Verifies the association was created successfully
    4. Confirms database record is created
    
    Args:
        test_user: Fixture providing authenticated user
        test_challenge: Fixture providing existing challenge
        test_post: Fixture providing existing post
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # Create user
    user_data = {
        "username": f"testuser-{uuid.uuid4().hex[:8]}",
        "email": f"testuser-{uuid.uuid4().hex[:8]}@test.com",
        "password": "testuser1",
        "full_name": "Test User",
        "bio": "Test bio"
    }
    
    # Register user
    register_response = client.post(
        "/api/v1/auth/register",
        json=user_data
    )
    
    if register_response.status_code != 200:
        pytest.fail(f"Failed to create test user: {register_response.json()}")
    
    user_id = register_response.json()["id"]
    
    # Login to get access token
    challenge_post_data = {
        "challenge_id": test_challenge["id"],
        "post_id": test_post["id"],
        "is_check_in": True
    }
    
    response = client.post(
        "/api/v1/challenges/post",
        headers=headers,
        json=challenge_post_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["challenge_id"] == test_challenge["id"]
    assert data["post_id"] == test_post["id"]
    assert data["is_check_in"] == True
    assert "submitted_at" in data
    
    # Verify record exists in database
    challenge_post = supabase.table("challenge_posts") \
        .select("*") \
        .eq("challenge_id", test_challenge["id"]) \
        .eq("post_id", test_post["id"]) \
        .execute()
    
    assert challenge_post.data
    assert len(challenge_post.data) > 0


def test_get_challenge_posts(test_user, test_challenge, test_post):
    """
    Test retrieving all posts for a specific challenge.
    
    This test:
    1. Gets posts associated with a challenge
    2. Verifies the test post appears in results
    3. Checks that post metadata is included
    
    Args:
        test_user: Fixture providing authenticated user
        test_challenge: Fixture providing existing challenge
        test_post: Fixture providing existing post
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    response = client.get(
        f"/api/v1/challenges/{test_challenge['id']}/posts",
        headers=headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    # Verify test post is in the response
    post_found = False
    for post in data:
        if post["id"] == test_post["id"]:
            post_found = True
            assert post["content"] == test_post["content"]
            assert "user" in post
            assert "challenge_post_details" in post
            assert post["challenge_post_details"]["challenge_id"] == test_challenge["id"]
            assert post["challenge_post_details"]["is_check_in"] == True
            break
    
    assert post_found, "Test post not found in challenge posts"


def test_add_another_post_to_challenge(test_user, test_challenge):
    """
    Test creating and adding a new post to a challenge.
    
    This test:
    1. Creates a new post directly for the test
    2. Adds it to the challenge as a non-check-in post
    3. Verifies the association was created successfully
    4. Cleans up the created post afterward
    
    Args:
        test_user: Fixture providing authenticated user
        test_challenge: Fixture providing existing challenge
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # Create a second post
    post_data = {
        "content": f"Another test post {uuid.uuid4().hex[:8]}",
        "media_urls": [BASE_ICON_URL],
        "is_private": False
    }
    
    post_response = client.post(
        "/api/v1/posts/",
        headers=headers,
        json=post_data
    )
    
    assert post_response.status_code == 200
    post_id = post_response.json()["id"]
    
    # Add to challenge as normal post (not check-in)
    challenge_post_data = {
        "challenge_id": test_challenge["id"],
        "post_id": post_id,
        "is_check_in": False
    }
    
    response = client.post(
        "/api/v1/challenges/post",
        headers=headers,
        json=challenge_post_data
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["challenge_id"] == test_challenge["id"]
    assert data["post_id"] == post_id
    assert data["is_check_in"] == False
    
    # Clean up: delete the additional post
    supabase.table("posts").delete().eq("id", post_id).execute()


def test_cannot_add_same_post_twice(test_user, test_challenge, test_post):
    """
    Test attempting to add the same post to a challenge twice.
    
    This test:
    1. Tries to add the test post to the challenge again
    2. Verifies that an error is returned
    3. Confirms the error message is appropriate
    
    Args:
        test_user: Fixture providing authenticated user
        test_challenge: Fixture providing existing challenge
        test_post: Fixture providing existing post
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    challenge_post_data = {
        "challenge_id": test_challenge["id"],
        "post_id": test_post["id"],
        "is_check_in": True
    }
    
    response = client.post(
        "/api/v1/challenges/post",
        headers=headers,
        json=challenge_post_data
    )
    
    assert response.status_code == 400
    assert "already added to the challenge" in response.json()["detail"]


def test_join_challenge_and_add_post(test_user, test_challenge):
    """
    Test joining a challenge and then adding a new post.
    
    This test:
    1. Makes user join the challenge
    2. Creates a new post for the challenge
    3. Adds the post to the challenge
    4. Verifies both operations work as expected
    5. Cleans up the created post afterward
    
    Args:
        test_user: Fixture providing authenticated user
        test_challenge: Fixture providing existing challenge
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # First join the challenge if not already joined
    join_data = {
        "challenge_id": test_challenge["id"]
    }
    
    # Skip validation of the join response since user might already be joined
    client.post(
        "/api/v1/challenges/join",
        headers=headers,
        json=join_data
    )
    
    # Create a new post
    post_data = {
        "content": f"Join and post test {uuid.uuid4().hex[:8]}",
        "media_urls": [BASE_ICON_URL],
        "is_private": False
    }
    
    post_response = client.post(
        "/api/v1/posts/",
        headers=headers,
        json=post_data
    )
    
    assert post_response.status_code == 200
    post_id = post_response.json()["id"]
    
    # Add to challenge as check-in
    challenge_post_data = {
        "challenge_id": test_challenge["id"],
        "post_id": post_id,
        "is_check_in": True
    }
    
    response = client.post(
        "/api/v1/challenges/post",
        headers=headers,
        json=challenge_post_data
    )
    
    assert response.status_code == 200
    
    # Verify challenge post is in challenge posts list
    challenge_posts_response = client.get(
        f"/api/v1/challenges/{test_challenge['id']}/posts",
        headers=headers
    )
    
    assert challenge_posts_response.status_code == 200
    posts_data = challenge_posts_response.json()
    
    post_found = False
    for post in posts_data:
        if post["id"] == post_id:
            post_found = True
            break
    
    assert post_found, "Newly added post not found in challenge posts"
    
    # Clean up: delete the post
    supabase.table("posts").delete().eq("id", post_id).execute()


def test_add_post_to_nonexistent_challenge(test_user, test_post):
    """
    Test adding a post to a challenge that doesn't exist.
    
    This test:
    1. Attempts to add a post to a non-existent challenge
    2. Verifies an appropriate error is returned
    
    Args:
        test_user: Fixture providing authenticated user
        test_post: Fixture providing existing post
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    fake_challenge_id = str(uuid.uuid4())
    challenge_post_data = {
        "challenge_id": fake_challenge_id,
        "post_id": test_post["id"],
        "is_check_in": True
    }
    
    response = client.post(
        "/api/v1/challenges/post",
        headers=headers,
        json=challenge_post_data
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_add_nonexistent_post_to_challenge(test_user, test_challenge):
    """
    Test adding a non-existent post to a challenge.
    
    This test:
    1. Attempts to add a non-existent post to a challenge
    2. Verifies an appropriate error is returned
    
    Args:
        test_user: Fixture providing authenticated user
        test_challenge: Fixture providing existing challenge
    """
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    fake_post_id = str(uuid.uuid4())
    challenge_post_data = {
        "challenge_id": test_challenge["id"],
        "post_id": fake_post_id,
        "is_check_in": True
    }
    
    response = client.post(
        "/api/v1/challenges/post",
        headers=headers,
        json=challenge_post_data
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"] 