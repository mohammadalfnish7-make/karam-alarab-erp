from __future__ import annotations

from fastapi.testclient import TestClient

from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, login_as


def _create_ops(admin_client: TestClient, email: str = "ops-edge@example.com") -> dict:
    response = admin_client.post(
        "/users",
        json={
            "email": email,
            "password": "ops-password-123",
            "roles": ["operations"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_user_rejects_short_password(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/users",
        json={
            "email": "short@example.com",
            "password": "short",
            "roles": ["operations"],
        },
    )
    assert response.status_code == 400


def test_create_user_rejects_empty_roles(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/users",
        json={
            "email": "norole@example.com",
            "password": "long-enough-password",
            "roles": [],
        },
    )
    assert response.status_code == 400


def test_create_user_rejects_unknown_role(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/users",
        json={
            "email": "badrole@example.com",
            "password": "long-enough-password",
            "roles": ["viewer"],
        },
    )
    assert response.status_code in {400, 404, 409}


def test_create_user_duplicate_email_is_409(admin_client: TestClient) -> None:
    _create_ops(admin_client, "dup@example.com")
    again = admin_client.post(
        "/users",
        json={
            "email": "dup@example.com",
            "password": "long-enough-password",
            "roles": ["operations"],
        },
    )
    assert again.status_code == 409


def test_list_users_pagination_boundaries(admin_client: TestClient) -> None:
    for i in range(3):
        _create_ops(admin_client, f"page-{i}@example.com")

    page1 = admin_client.get("/users", params={"page": 1, "pageSize": 2})
    assert page1.status_code == 200
    body = page1.json()
    assert body["page"] == 1
    assert body["pageSize"] == 2
    assert len(body["data"]) == 2
    assert body["total"] >= 3

    bad = admin_client.get("/users", params={"page": 1, "pageSize": 101})
    assert bad.status_code == 400

    zero = admin_client.get("/users", params={"page": 0, "pageSize": 25})
    assert zero.status_code == 400


def test_ops_cannot_list_users(admin_client: TestClient) -> None:
    _create_ops(admin_client)
    login_as(admin_client, "ops-edge@example.com", "ops-password-123")
    response = admin_client.get("/users")
    assert response.status_code == 403


def test_ops_cannot_create_user(admin_client: TestClient) -> None:
    _create_ops(admin_client, "ops-create@example.com")
    login_as(admin_client, "ops-create@example.com", "ops-password-123")
    response = admin_client.post(
        "/users",
        json={
            "email": "blocked@example.com",
            "password": "long-enough-password",
            "roles": ["operations"],
        },
    )
    assert response.status_code == 403


def test_deactivate_user_revokes_session(admin_client: TestClient) -> None:
    user = _create_ops(admin_client, "deact@example.com")
    ops = TestClient(admin_client.app)
    login_as(ops, "deact@example.com", "ops-password-123")
    assert ops.get("/users/me").status_code == 200

    patch = admin_client.patch(f"/users/{user['id']}", json={"is_active": False})
    assert patch.status_code == 200
    assert patch.json()["is_active"] is False
    assert ops.get("/users/me").status_code == 401


def test_reactivate_user(admin_client: TestClient) -> None:
    user = _create_ops(admin_client, "react@example.com")
    admin_client.patch(f"/users/{user['id']}", json={"is_active": False})
    again = admin_client.patch(f"/users/{user['id']}", json={"is_active": True})
    assert again.status_code == 200
    assert again.json()["is_active"] is True


def test_update_roles_to_operations(admin_client: TestClient) -> None:
    user = admin_client.post(
        "/users",
        json={
            "email": "sales-to-ops@example.com",
            "password": "long-enough-password",
            "roles": ["sales"],
        },
    ).json()
    response = admin_client.patch(
        f"/users/{user['id']}",
        json={"roles": ["operations"]},
    )
    assert response.status_code == 200
    assert response.json()["roles"] == ["operations"]


def test_patch_user_requires_body_fields(admin_client: TestClient) -> None:
    user = _create_ops(admin_client, "empty-patch@example.com")
    response = admin_client.patch(f"/users/{user['id']}", json={})
    assert response.status_code == 400


def test_set_role_permissions_and_ops_sees_them(admin_client: TestClient) -> None:
    grant = admin_client.put(
        "/roles/operations/permissions",
        json={"permissions": ["work:read", "process:read"]},
    )
    assert grant.status_code == 204
    _create_ops(admin_client, "ops-perms@example.com")
    login_as(admin_client, "ops-perms@example.com", "ops-password-123")
    me = admin_client.get("/users/me").json()
    assert "work:read" in me["permissions"]
    assert "identity_access:update" not in me["permissions"]


def test_register_permission_invalid_name(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/permissions/register",
        json={"permissions": ["Not A Permission"]},
    )
    assert response.status_code == 400


def test_change_password_wrong_current(admin_client: TestClient) -> None:
    response = admin_client.patch(
        "/users/me/password",
        json={
            "current_password": "definitely-wrong-password",
            "new_password": "brand-new-password-99",
        },
    )
    assert response.status_code == 401


def test_inactive_user_cannot_login(admin_client: TestClient) -> None:
    user = _create_ops(admin_client, "inactive-login@example.com")
    admin_client.patch(f"/users/{user['id']}", json={"is_active": False})
    client = TestClient(admin_client.app)
    response = client.post(
        "/sessions",
        json={"email": "inactive-login@example.com", "password": "ops-password-123"},
    )
    assert response.status_code == 401


def test_admin_can_still_login_after_ops_created(
    admin_client: TestClient,
) -> None:
    _create_ops(admin_client, "keep-admin@example.com")
    login_as(admin_client, ADMIN_EMAIL, ADMIN_PASSWORD)
    me = admin_client.get("/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == ADMIN_EMAIL
