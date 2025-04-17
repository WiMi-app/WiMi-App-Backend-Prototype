import json
import uuid
from datetime import datetime
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


@pytest.fixture(scope="module")
def test_user_credentials():
    """Create test user credentials"""
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "testpassword123"
    
    yield {
        "username": username,
        "email": email,
        "password": password,
        "full_name": "Test User",
        "bio": "Test bio",
    }


def test_register_user(test_user_credentials):
    """Test registering a new user"""
    response = client.post(
        "/api/v1/auth/register",
        json=test_user_credentials
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["username"] == test_user_credentials["username"]
    assert data["email"] == test_user_credentials["email"]
    assert "id" in data
    assert "password_hash" not in data  # Ensure password hash is not returned
    
    # Clean up: delete the test user
    supabase.table("users").delete().eq("id", data["id"]).execute()


def test_register_duplicate_email(test_user_credentials):
    """Test registering with an email that already exists"""
    # Register first user
    first_response = client.post(
        "/api/v1/auth/register",
        json=test_user_credentials
    )
    
    assert first_response.status_code == 200
    
    # Try to register with the same email but different username
    duplicate_credentials = test_user_credentials.copy()
    duplicate_credentials["username"] = f"another_{test_user_credentials['username']}"
    
    second_response = client.post(
        "/api/v1/auth/register",
        json=duplicate_credentials
    )
    
    assert second_response.status_code == 400
    assert "Email already registered" in second_response.json()["detail"]
    
    # Clean up: delete the first test user
    first_user_id = first_response.json()["id"]
    supabase.table("users").delete().eq("id", first_user_id).execute()


def test_register_duplicate_username(test_user_credentials):
    """Test registering with a username that already exists"""
    # Register first user
    first_response = client.post(
        "/api/v1/auth/register",
        json=test_user_credentials
    )
    
    assert first_response.status_code == 200
    
    # Try to register with the same username but different email
    duplicate_credentials = test_user_credentials.copy()
    duplicate_credentials["email"] = f"another_{test_user_credentials['email']}"
    
    second_response = client.post(
        "/api/v1/auth/register",
        json=duplicate_credentials
    )
    
    assert second_response.status_code == 400
    assert "Username already taken" in second_response.json()["detail"]
    
    # Clean up: delete the first test user
    first_user_id = first_response.json()["id"]
    supabase.table("users").delete().eq("id", first_user_id).execute()


def test_login_with_username(test_user_credentials):
    """Test logging in with username and password"""
    # Register user first
    register_response = client.post(
        "/api/v1/auth/register",
        json=test_user_credentials
    )
    
    assert register_response.status_code == 200
    user_id = register_response.json()["id"]
    
    # Now login with username
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user_credentials["username"],
            "password": test_user_credentials["password"]
        }
    )
    
    assert login_response.status_code == 200
    token_data = login_response.json()
    
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user_id"] == user_id
    assert "expires" in token_data
    
    # Clean up: delete the test user
    supabase.table("users").delete().eq("id", user_id).execute()


def test_login_with_email(test_user_credentials):
    """Test logging in with email and password"""
    # Register user first
    register_response = client.post(
        "/api/v1/auth/register",
        json=test_user_credentials
    )
    
    assert register_response.status_code == 200
    user_id = register_response.json()["id"]
    
    # Now login with email
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        }
    )
    
    assert login_response.status_code == 200
    token_data = login_response.json()
    
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user_id"] == user_id
    assert "expires" in token_data
    
    # Clean up: delete the test user
    supabase.table("users").delete().eq("id", user_id).execute()


def test_login_email_endpoint(test_user_credentials):
    """Test logging in with the specific email login endpoint"""
    # Register user first
    register_response = client.post(
        "/api/v1/auth/register",
        json=test_user_credentials
    )
    
    assert register_response.status_code == 200
    user_id = register_response.json()["id"]
    
    # Now login with email endpoint
    login_response = client.post(
        "/api/v1/auth/login/email",
        json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        }
    )
    
    assert login_response.status_code == 200
    token_data = login_response.json()
    
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user_id"] == user_id
    assert "expires" in token_data
    
    # Clean up: delete the test user
    supabase.table("users").delete().eq("id", user_id).execute()


def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent_user",
            "password": "wrong_password"
        }
    )
    
    assert login_response.status_code == 401
    assert "Incorrect email/username or password" in login_response.json()["detail"]


def test_login_email_invalid_credentials():
    """Test login with email endpoint using invalid credentials"""
    login_response = client.post(
        "/api/v1/auth/login/email",
        json={
            "email": "nonexistent@example.com",
            "password": "wrong_password"
        }
    )
    
    assert login_response.status_code == 401
    assert "Incorrect email or password" in login_response.json()["detail"] 