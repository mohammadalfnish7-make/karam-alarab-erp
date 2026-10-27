from __future__ import annotations

from fastapi.testclient import TestClient

ADMIN_EMAIL = "admin@karam-alarab.com"
ADMIN_PASSWORD = "test-admin-password-123"


def login_as(client: TestClient, email: str, password: str) -> TestClient:
    client.cookies.clear()
    response = client.post("/sessions", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    return client
