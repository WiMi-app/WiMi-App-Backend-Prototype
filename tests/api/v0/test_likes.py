import pytest
from types import SimpleNamespace
from app.api.v0.likes import like_post, unlike_post
from app.schemas.likes import LikeCreate

# Integration tests
def test_like_and_unlike_integration(client, auth_headers):
    posts = client.get("/api/v0/posts/").json()
    assert posts
    
    post_id = posts[0]["id"]
    
    # Like a post
    resp = client.post(
        "/api/v0/likes/",
        json={"post_id": post_id},
        headers={**auth_headers, "Idempotency-Key": "test-key"}
    )
    assert resp.status_code == 201
    
    data = resp.json()
    like_id = data["id"]
    assert data["post_id"] == post_id
    
    # Unlike the post
    resp2 = client.delete(f"/api/v0/likes/{like_id}", headers=auth_headers)
    assert resp2.status_code == 204

