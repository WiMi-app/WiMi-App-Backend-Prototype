import types
from types import SimpleNamespace
import pytest
from app.api.v0.posts import create_post, list_posts
from app.schemas.posts import PostCreate

# Integration tests
def test_list_posts_integration(client):
    resp = client.get("/api/v0/posts/")
    assert resp.status_code == 200
    
    posts = resp.json()
    assert isinstance(posts, list)
    assert len(posts) >= 4

def test_get_post_integration(client):
    posts = client.get("/api/v0/posts/").json()
    assert posts
    
    post = posts[0]
    resp = client.get(f"/api/v0/posts/{post['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == post["id"]

def test_create_update_delete_post_integration(client, auth_headers):
    challenges = client.get("/api/v0/challenges/").json()
    assert challenges
    
    challenge_id = challenges[0]["id"]
    
    # Create
    payload = {"challenge_id": challenge_id, "content_url": "http://example.com/test.jpg"}
    resp = client.post("/api/v0/posts/", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    
    data = resp.json()
    post_id = data["id"]
    assert data["challenge_id"] == challenge_id
    assert data["content_url"] == "http://example.com/test.jpg"
    
    # Update
    update_payload = {"content_url": "http://example.com/updated.jpg"}
    resp2 = client.put(f"/api/v0/posts/{post_id}", json=update_payload, headers=auth_headers)
    assert resp2.status_code == 200
    assert resp2.json()["content_url"] == "http://example.com/updated.jpg"
    
    # Delete
    resp3 = client.delete(f"/api/v0/posts/{post_id}", headers=auth_headers)
    assert resp3.status_code == 204
    assert client.get(f"/api/v0/posts/{post_id}").status_code == 404 