from __future__ import annotations

from fastapi.testclient import TestClient

from helpers import login_as


def test_seed_operations_user_can_login(client: TestClient) -> None:
    login_as(client, "ops@karam-alarab.com", "test-ops-password-123")
    me = client.get("/users/me")
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "ops@karam-alarab.com"
    assert "operations" in body["roles"]
    assert body["is_superuser"] is False
    assert "work:read" in body["permissions"]
    assert "identity_access:update" not in body["permissions"]
