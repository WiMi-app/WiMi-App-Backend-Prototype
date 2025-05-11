import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_signup_and_login_integration(client):
    email = "wimiapp.official@gmail.com"
    password = "password123"
    
    # Signup
    resp = client.post("/api/v0/auth/signup", json={"email": email, "password": password})
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == email
    
    # Login
    resp2 = client.post("/api/v0/auth/token", data={"username": email, "password": password})
    assert resp2.status_code == 200
    token_data = resp2.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer" 
    

@pytest.fixture
def client():
    return TestClient(app)

def test_login_and_refresh(client):
    email = "suhan.park@example.com"
    pw = "1234spark"

    # 1) Sign up
    signup = client.post("/api/v0/auth/signup", json={"email": email, "password": pw})
    assert signup.status_code == 201

    # 2) Log in — this will set both access_token and refresh_token cookies on client
    login = client.post(
        "/api/v0/auth/token",
        data={"username": email, "password": pw},
        # TestClient uses form-encoding automatically for `data=`
    )
    assert login.status_code == 200
    tokens = login.json()
    assert "refresh_token" in tokens

    # 3) Now call refresh — TestClient will automatically send the cookie it got
    refresh = client.post("/api/v0/auth/refresh")
    assert refresh.status_code == 200
    new_tokens = refresh.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens