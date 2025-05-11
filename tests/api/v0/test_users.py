import pytest


def test_read_me(client, auth_headers):
    resp = client.get("/api/v0/users/me", headers=auth_headers)
    assert resp.status_code == 200
    user = resp.json()
    assert "email" in user and user["email"] == "testuser@example.com"

def test_update_me(client, auth_headers):
    resp = client.put("/api/v0/users/me", json={"full_name": "Jack Doe"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Jack Doe"

def test_read_user_not_found(client):
    resp = client.get("/api/v0/users/nonexistent-id")
    assert resp.status_code == 404

def test_read_user_integration(client, auth_headers):
    me = client.get("/api/v0/users/me", headers=auth_headers).json()
    user_id = me["id"]
    resp = client.get(f"/api/v0/users/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["email"] == me["email"]
