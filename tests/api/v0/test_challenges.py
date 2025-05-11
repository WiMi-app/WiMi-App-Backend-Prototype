import types
from types import SimpleNamespace

import pytest

from app.api.v0.challenges import (create_challenge, delete_challenge,
                                   get_challenge, list_challenges,
                                   update_challenge)
from app.schemas.challenges import ChallengeCreate, ChallengeUpdate


# Integration tests
def test_list_challenges_integration(client):
    resp = client.get("/api/v0/challenges/")
    assert resp.status_code == 200
    
    challenges = resp.json()
    assert isinstance(challenges, list)
    assert len(challenges) >= 4

def test_get_challenge_integration(client):
    challenges = client.get("/api/v0/challenges/").json()
    assert challenges
    
    challenge = challenges[0]
    resp = client.get(f"/api/v0/challenges/{challenge['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == challenge["id"]

def test_create_update_delete_challenge_integration(client, auth_headers):
    # Create
    payload = {"title": "Test Chal", "description": "Desc", "frequency_days": 1}
    resp = client.post("/api/v0/challenges/", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    
    data = resp.json()
    cid = data["id"]
    assert data["title"] == "Test Chal"
    
    # Update
    update_payload = {"description": "Updated"}
    resp2 = client.put(f"/api/v0/challenges/{cid}", json=update_payload, headers=auth_headers)
    assert resp2.status_code == 200
    assert resp2.json()["description"] == "Updated"
    
    # Delete
    resp3 = client.delete(f"/api/v0/challenges/{cid}", headers=auth_headers)
    assert resp3.status_code == 204
    assert client.get(f"/api/v0/challenges/{cid}").status_code == 404 