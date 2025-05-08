import pytest
import types
from types import SimpleNamespace
from app.api.v0.notifications import list_notifications, mark_read, mark_all_read

def test_list_and_mark_notifications(client, auth_headers):
    # create a notification via direct supabase call or assume one exists
    resp = client.get("/api/v0/notifications/?page=1&per_page=10", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # bulk mark all read
    resp2 = client.post("/api/v0/notifications/read_all", headers=auth_headers)
    assert resp2.status_code == 200
    assert "updated_count" in resp2.json()

def test_mark_single_notification_read_integration(client, auth_headers):
    notifications = client.get("/api/v0/notifications/?page=1&per_page=10", headers=auth_headers).json()
   
    if not notifications:
        pytest.skip("No notifications to mark_read")
        
    nid = notifications[0]["id"]
    resp = client.post(f"/api/v0/notifications/read/{nid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

