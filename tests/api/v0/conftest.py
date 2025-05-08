import pytest
from fastapi.testclient import TestClient
from app.main import app
import random

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

@pytest.fixture(scope="session")
def auth_headers(client):
    # sign up a new random user and grab a token
    email = f"testuser{random.randint(1,100000)}@example.com"
    pw = "password123"
    client.post("/api/v0/auth/signup", json={"email": email, "password": pw})
    token = client.post("/api/v0/auth/token", data={"username": email, "password": pw}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"} 