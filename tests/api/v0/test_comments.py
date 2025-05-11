import pytest


def test_list_comments_integration(client):
    posts = client.get("/api/v0/posts/").json()
    
    for post in posts:
        resp = client.get("/api/v0/comments/", params={"post_id": post["id"]})
        assert resp.status_code == 200
        comments = resp.json()
        
        if comments:
            assert all(c["post_id"] == post["id"] for c in comments)
            return
        
    pytest.skip("No comments available for integration test")

def test_get_comment_integration(client):
    comments = client.get("/api/v0/comments/").json()
    
    if not comments:
        pytest.skip("No comments available for integration test")
        
    comment = comments[0]
    resp = client.get(f"/api/v0/comments/{comment['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == comment["id"]

def test_create_update_delete_comment_integration(client, auth_headers):
    posts = client.get("/api/v0/posts/").json()
    post_id = posts[0]["id"]
    
    # Create
    payload = {"post_id": post_id, "content": "Test comment"}
    resp = client.post("/api/v0/comments/", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    
    data = resp.json()
    comment_id = data["id"]
    assert data["content"] == "Test comment"
    
    # Update
    update_payload = {"content": "Updated comment"}
    resp2 = client.put(f"/api/v0/comments/{comment_id}", json=update_payload, headers=auth_headers)
    assert resp2.status_code == 200
    assert resp2.json()["content"] == "Updated comment"
    
    # Delete
    resp3 = client.delete(f"/api/v0/comments/{comment_id}", headers=auth_headers)
    assert resp3.status_code == 204
    assert client.get(f"/api/v0/comments/{comment_id}").status_code == 404 