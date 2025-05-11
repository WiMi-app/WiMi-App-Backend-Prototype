from types import SimpleNamespace

import pytest

from app.api.v0.follows import follow_user, unfollow_user
from app.schemas.follows import FollowCreate


# Integration tests
def test_cannot_follow_self_integration(client, auth_headers):
    me = client.get("/api/v0/users/me", headers=auth_headers).json()
    resp = client.post("/api/v0/follows/", json={"followee_id": me["id"]}, headers=auth_headers)
    assert resp.status_code == 400

