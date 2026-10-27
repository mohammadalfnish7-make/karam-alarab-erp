from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from database.models.audit import AuditEntryRow
from helpers import login_as
from config.settings import Settings
from database.engine import create_db_engine, create_session_factory


def _create_sales(admin_client: TestClient) -> dict:
    response = admin_client.post(
        "/users",
        json={
            "email": "sales@example.com",
            "password": "sales-password-12",
            "roles": ["sales"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_sales_cannot_create_users(admin_client: TestClient) -> None:
    _create_sales(admin_client)
    login_as(admin_client, "sales@example.com", "sales-password-12")
    response = admin_client.post(
        "/users",
        json={
            "email": "other@example.com",
            "password": "other-password-12",
            "roles": ["sales"],
        },
    )
    assert response.status_code == 403


def test_other_user_id_is_404_for_sales(admin_client: TestClient) -> None:
    sales = _create_sales(admin_client)
    admin_me = admin_client.get("/users/me").json()
    login_as(admin_client, "sales@example.com", "sales-password-12")
    response = admin_client.get(f"/users/{admin_me['id']}")
    assert response.status_code == 404
    # Own profile via /users/{id} is allowed without identity_access:read
    own = admin_client.get(f"/users/{sales['id']}")
    assert own.status_code == 200


def test_last_admin_deactivate_is_409(admin_client: TestClient) -> None:
    me = admin_client.get("/users/me").json()
    response = admin_client.patch(
        f"/users/{me['id']}",
        json={"is_active": False},
    )
    assert response.status_code == 409


def test_unknown_permission_denied(admin_client: TestClient) -> None:
    _create_sales(admin_client)
    login_as(admin_client, "sales@example.com", "sales-password-12")
    # Sales lacks identity_access:read
    response = admin_client.get("/permissions")
    assert response.status_code == 403


def test_register_new_permission_without_catalog_enum_change(
    admin_client: TestClient,
) -> None:
    created = admin_client.post(
        "/permissions/register",
        json={"permissions": ["example:read"]},
    )
    assert created.status_code == 201
    assert "example:read" in created.json()

    grant = admin_client.put(
        "/roles/sales/permissions",
        json={"permissions": ["example:read"]},
    )
    assert grant.status_code == 204

    _create_sales(admin_client)
    login_as(admin_client, "sales@example.com", "sales-password-12")
    me = admin_client.get("/users/me")
    assert me.status_code == 200
    assert "example:read" in me.json()["permissions"]


def test_create_user_writes_audit_row(
    admin_client: TestClient,
    settings: Settings,
) -> None:
    response = admin_client.post(
        "/users",
        json={
            "email": "ops@example.com",
            "password": "ops-password-123",
            "roles": ["operations"],
        },
    )
    assert response.status_code == 201
    engine = create_db_engine(settings)
    session = create_session_factory(engine)()
    try:
        rows = session.scalars(
            select(AuditEntryRow).where(AuditEntryRow.action == "UserRegistered")
        ).all()
        assert any("ops@example.com" in row.actor for row in rows)
    finally:
        session.close()
        engine.dispose()


def test_guessed_uuid_is_404(admin_client: TestClient) -> None:
    response = admin_client.get(f"/users/{uuid4()}")
    # Admin has read — missing user is still 404
    assert response.status_code == 404
