import pytest
import time
from unittest.mock import patch
from uuid import uuid4
from fastapi import status


@pytest.fixture
def google_oauth_data():
    return {
        "token": "google_mock_token",
        "provider": "google",
    }


@pytest.fixture
def apple_oauth_data():
    return {
        "token": "apple_mock_token",
        "provider": "apple",
    }


def test_register_new_user(client, supabase_mock):
    """Test user registration with email."""
    # Arrange
    new_user = {
        "username": "newuser",
        "email": "new@example.com",
        "password": "password123",
        "full_name": "New User"
    }
    
    # Act
    start_time = time.time()
    response = client.post("/api/v0/auth/register", json=new_user)
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "id" in response.json()
    assert response.json()["username"] == new_user["username"]
    assert response.json()["email"] == new_user["email"]
    assert response.json()["full_name"] == new_user["full_name"]
    # Password should not be returned
    assert "password" not in response.json()
    # Verify data was correctly stored in mock
    assert len([u for u in supabase_mock.tables["users"].data if u["username"] == new_user["username"]]) == 1


def test_register_duplicate_username(client, supabase_mock):
    """Test registration with duplicate username fails."""
    # Arrange
    existing_user = supabase_mock.test_users[0]
    new_user = {
        "username": existing_user["username"],  # Duplicate username
        "email": "different@example.com",
        "password": "password123",
        "full_name": "Different User"
    }
    
    # Act
    response = client.post("/api/v0/auth/register", json=new_user)
    
    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Username already taken" in response.json()["detail"]


def test_register_duplicate_email(client, supabase_mock):
    """Test registration with duplicate email fails."""
    # Arrange
    existing_user = supabase_mock.test_users[0]
    new_user = {
        "username": "uniqueuser",
        "email": existing_user["email"],  # Duplicate email
        "password": "password123",
        "full_name": "Unique User"
    }
    
    # Act
    response = client.post("/api/v0/auth/register", json=new_user)
    
    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email already registered" in response.json()["detail"]


def test_login_with_email_success(client, supabase_mock):
    """Test successful login with email and password."""
    # Arrange
    login_data = {
        "email": supabase_mock.test_users[0]["email"],
        "password": "password"  # This matches the hashed password in the mock
    }
    
    # Act
    start_time = time.time()
    response = client.post("/api/v0/auth/login/email", json=login_data)
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "token_type" in response.json()
    assert "user_id" in response.json()
    assert response.json()["token_type"] == "bearer"
    assert duration < 0.005  # Less than 5ms


def test_login_with_email_invalid_credentials(client):
    """Test login with invalid credentials fails."""
    # Arrange
    login_data = {
        "email": "test@example.com",
        "password": "wrong_password"
    }
    
    # Act
    response = client.post("/api/v0/auth/login/email", json=login_data)
    
    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_with_oauth2_form(client, supabase_mock):
    """Test login with OAuth2 password request form."""
    # Arrange - use form data for this test
    form_data = {
        "username": supabase_mock.test_users[0]["email"],  # Can be email or username
        "password": "password"
    }
    
    # Act
    start_time = time.time()
    response = client.post("/api/v0/auth/login", data=form_data)
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "token_type" in response.json()
    assert duration < 0.005  # Less than 5ms


@patch('app.api.v0.auth.verify_google_token')
def test_google_oauth_login(mock_verify_google_token, client, google_oauth_data):
    """Test login with Google OAuth."""
    # Arrange
    mock_verify_google_token.return_value = {
        "sub": str(uuid4()),
        "email": "google_user@example.com",
        "name": "Google User",
        "picture": "https://example.com/google_avatar.jpg"
    }
    
    # Act
    start_time = time.time()
    response = client.post("/api/v0/auth/oauth/google", json=google_oauth_data)
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "user_id" in response.json()
    assert duration < 0.005  # Less than 5ms


@patch('app.api.v0.auth.verify_apple_token')
def test_apple_oauth_login(mock_verify_apple_token, client, apple_oauth_data):
    """Test login with Apple OAuth."""
    # Arrange
    mock_verify_apple_token.return_value = {
        "sub": str(uuid4()),
        "email": "apple_user@example.com",
        "name": "Apple User"
    }
    
    # Act
    start_time = time.time()
    response = client.post("/api/v0/auth/oauth/apple", json=apple_oauth_data)
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "user_id" in response.json()
    assert duration < 0.005  # Less than 5ms


def test_verify_token(client, auth_headers):
    """Test token verification endpoint."""
    # Act
    start_time = time.time()
    response = client.get("/api/v0/auth/verify-token", headers=auth_headers)
    duration = time.time() - start_time
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert "user_id" in response.json()
    assert duration < 0.005  # Less than 5ms


def test_verify_token_invalid(client):
    """Test token verification with invalid token fails."""
    # Act
    response = client.get(
        "/api/v0/auth/verify-token", 
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED 


def test_login_rate_limiting(client):
    """Test rate limiting for multiple failed login attempts."""
    # Arrange - incorrect login data
    login_data = {
        "email": "test@example.com",
        "password": "wrong_password"
    }
    
    # Act - make multiple login attempts in quick succession
    responses = []
    for _ in range(6):  # Assuming rate limit kicks in after 5 attempts
        response = client.post("/api/v0/auth/login/email", json=login_data)
        responses.append(response)
    
    # Assert
    # The first few attempts should return 401 Unauthorized
    assert responses[0].status_code == status.HTTP_401_UNAUTHORIZED
    
    # Later attempts should be rate limited with 429 Too Many Requests
    # This assumes rate limiting is configured on the backend
    rate_limited = any(r.status_code == status.HTTP_429_TOO_MANY_REQUESTS for r in responses)
    assert rate_limited, "No rate limiting detected after multiple failed login attempts"
    
    # Check for appropriate headers on rate limited response
    rate_limited_response = next((r for r in responses if r.status_code == status.HTTP_429_TOO_MANY_REQUESTS), None)
    if rate_limited_response:
        assert "Retry-After" in rate_limited_response.headers or "X-RateLimit-Reset" in rate_limited_response.headers 