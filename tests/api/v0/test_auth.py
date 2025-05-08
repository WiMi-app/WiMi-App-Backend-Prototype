import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from app.main import app
from app.core.config import settings
from app.schemas.auth import TokenData
from app.schemas.users import UserCreate

client = TestClient(app)

def test_login_success():
    """Test successful login with valid credentials"""
    # First register a test user
    user_data = {
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    client.post("/api/v0/auth/register", json=user_data)
    
    # Then try to login
    response = client.post(
        "/api/v0/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user_id" in data
    assert "expires" in data

def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    response = client.post(
        "/api/v0/auth/login",
        data={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email/username or password"

def test_login_missing_credentials():
    """Test login with missing credentials"""
    response = client.post(
        "/api/v0/auth/login",
        data={}
    )
    assert response.status_code == 422  # Validation error

def test_register_success():
    """Test successful user registration"""
    user_data = {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "newpassword123",
        "full_name": "New User"
    }
    response = client.post("/api/v0/auth/register", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert "id" in data
    assert "password" not in data  # Ensure password is not returned

def test_register_duplicate_email():
    """Test registration with existing email"""
    # First register a user
    user_data = {
        "email": "duplicate@example.com",
        "username": "user1",
        "password": "password123",
        "full_name": "User One"
    }
    client.post("/api/v0/auth/register", json=user_data)
    
    # Try to register another user with same email
    duplicate_data = {
        "email": "duplicate@example.com",
        "username": "user2",
        "password": "password123",
        "full_name": "User Two"
    }
    response = client.post("/api/v0/auth/register", json=duplicate_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_register_duplicate_username():
    """Test registration with existing username"""
    # First register a user
    user_data = {
        "email": "user1@example.com",
        "username": "duplicateuser",
        "password": "password123",
        "full_name": "User One"
    }
    client.post("/api/v0/auth/register", json=user_data)
    
    # Try to register another user with same username
    duplicate_data = {
        "email": "user2@example.com",
        "username": "duplicateuser",
        "password": "password123",
        "full_name": "User Two"
    }
    response = client.post("/api/v0/auth/register", json=duplicate_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already taken"

def test_register_invalid_data():
    """Test registration with invalid data"""
    user_data = {
        "email": "invalid-email",
        "username": "u",  # Too short
        "password": "123",  # Too short
        "full_name": ""
    }
    response = client.post("/api/v0/auth/register", json=user_data)
    assert response.status_code == 422  # Validation error

def test_verify_token_success():
    """Test token verification with valid token"""
    # First register and login to get a valid token
    user_data = {
        "email": "verify@example.com",
        "username": "verifyuser",
        "password": "verifypass123",
        "full_name": "Verify User"
    }
    client.post("/api/v0/auth/register", json=user_data)
    
    login_response = client.post(
        "/api/v0/auth/login",
        data={
            "username": "verifyuser",
            "password": "verifypass123"
        }
    )
    token = login_response.json()["access_token"]
    
    # Test token verification
    response = client.get(
        "/api/v0/auth/verify-token",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "user_id" in data
    assert "username" in data
    assert "email" in data
    assert data["username"] == "verifyuser"

def test_verify_token_invalid():
    """Test token verification with invalid token"""
    response = client.get(
        "/api/v0/auth/verify-token",
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401

def test_verify_token_missing():
    """Test token verification without token"""
    response = client.get("/api/v0/auth/verify-token")
    assert response.status_code == 401 