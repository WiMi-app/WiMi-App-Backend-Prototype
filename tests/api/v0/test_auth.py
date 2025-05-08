import pytest

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