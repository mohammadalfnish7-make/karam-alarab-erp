from __future__ import annotations

from fastapi.testclient import TestClient

from helpers import ADMIN_EMAIL, ADMIN_PASSWORD


def test_login_success_sets_httponly_cookie(client: TestClient) -> None:
    response = client.post(
        "/sessions",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == ADMIN_EMAIL
    assert "identity_access:update" in body["permissions"]
    cookie = response.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie or "httponly" in cookie.lower()
    assert "karam_session=" in cookie


def test_login_failure_is_generic_401(client: TestClient) -> None:
    response = client.post(
        "/sessions",
        json={"email": ADMIN_EMAIL, "password": "wrong-password-xx"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password."

    response2 = client.post(
        "/sessions",
        json={"email": "nobody@example.com", "password": "wrong-password-xx"},
    )
    assert response2.status_code == 401
    assert response2.json()["error"]["message"] == "Invalid email or password."


def test_unauthenticated_me_is_401(client: TestClient) -> None:
    response = client.get("/users/me")
    assert response.status_code == 401


def test_password_change_invalidates_session(admin_client: TestClient) -> None:
    response = admin_client.patch(
        "/users/me/password",
        json={
            "current_password": ADMIN_PASSWORD,
            "new_password": "brand-new-password-99",
        },
    )
    assert response.status_code == 204
    me = admin_client.get("/users/me")
    assert me.status_code == 401

    login = admin_client.post(
        "/sessions",
        json={"email": ADMIN_EMAIL, "password": "brand-new-password-99"},
    )
    assert login.status_code == 201


def test_logout(admin_client: TestClient) -> None:
    response = admin_client.delete("/sessions/current")
    assert response.status_code == 204
    assert admin_client.get("/users/me").status_code == 401
