from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, login_as
from notify.application.delivery_worker import process_pending_deliveries
from notify.domain.signing import verify_webhook_signature


def _create_workflow(admin_client: TestClient) -> str:
    response = admin_client.post(
        "/workflows",
        json={
            "name": f"wf-{uuid4().hex[:8]}",
            "statuses": [
                {"key": "todo", "name": "To do", "is_initial": True},
                {"key": "doing", "name": "Doing", "is_initial": False},
                {"key": "done", "name": "Done", "is_initial": False},
            ],
            "transitions": [
                {"from_status_key": "todo", "to_status_key": "doing", "name": "start"},
                {"from_status_key": "doing", "to_status_key": "done", "name": "finish"},
                {"from_status_key": "doing", "to_status_key": "todo", "name": "reopen"},
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_type(admin_client: TestClient, workflow_id: str, key: str | None = None) -> str:
    response = admin_client.post(
        "/task-types",
        json={
            "key": key or f"type_{uuid4().hex[:8]}",
            "name": "Ops item",
            "workflow_id": workflow_id,
            "hierarchy_level": "standard",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_empty_task_type_catalog(admin_client: TestClient) -> None:
    response = admin_client.get("/task-types")
    assert response.status_code == 200
    assert response.json() == []


def test_error_messages_are_readable(admin_client: TestClient) -> None:
    missing = admin_client.post("/workflows", json={})
    assert missing.status_code == 400
    body = missing.json()["error"]
    assert body["message"] == "Please fix the highlighted fields and try again."
    assert "required" in body["fields"]["name"].lower()

    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    task_id = admin_client.post(
        "/tasks",
        json={"task_type_id": type_id, "title": "Readable"},
    ).json()["id"]
    bad = admin_client.post(
        f"/tasks/{task_id}/transitions",
        json={"to_status_key": "done"},
    )
    assert bad.status_code == 409
    assert "cannot move" in bad.json()["error"]["message"].lower()
    assert "workflow" in bad.json()["error"]["message"].lower()


def test_create_task_requires_active_type(admin_client: TestClient) -> None:
    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    admin_client.patch(f"/task-types/{type_id}", json={"is_active": False})
    response = admin_client.post(
        "/tasks",
        json={"task_type_id": type_id, "title": "Should fail"},
    )
    assert response.status_code == 400


def test_task_lifecycle_steps_comment_link_attach(admin_client: TestClient) -> None:
    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    create = admin_client.post(
        "/tasks",
        json={"task_type_id": type_id, "title": "Receive cargo", "description": "note"},
    )
    assert create.status_code == 201, create.text
    task = create.json()
    assert task["statusKey"] == "todo"
    task_id = task["id"]

    bad = admin_client.post(
        f"/tasks/{task_id}/transitions",
        json={"to_status_key": "done"},
    )
    assert bad.status_code == 409

    ok = admin_client.post(
        f"/tasks/{task_id}/transitions",
        json={"to_status_key": "doing"},
    )
    assert ok.status_code == 200
    assert ok.json()["statusKey"] == "doing"

    step = admin_client.post(f"/tasks/{task_id}/steps", json={"title": "Check seal"})
    assert step.status_code == 201
    step_id = step.json()["steps"][0]["id"]
    done = admin_client.patch(
        f"/tasks/{task_id}/steps/{step_id}",
        json={"is_done": True},
    )
    assert done.json()["steps"][0]["isDone"] is True

    comment = admin_client.post(
        f"/tasks/{task_id}/comments",
        json={"body": "Looks good"},
    )
    assert comment.status_code == 201
    assert len(comment.json()["comments"]) == 1

    link = admin_client.post(
        f"/tasks/{task_id}/entity-links",
        json={"entity_type": "shipment", "entity_id": str(uuid4())},
    )
    assert link.status_code == 201

    other = admin_client.post(
        "/tasks",
        json={"task_type_id": type_id, "title": "Sibling"},
    ).json()
    peer = admin_client.post(
        f"/tasks/{task_id}/links",
        json={"to_task_id": other["id"], "link_type": "relates"},
    )
    assert peer.status_code == 201

    upload = admin_client.post(
        f"/tasks/{task_id}/attachments",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    attachment_id = upload.json()["attachments"][0]["id"]
    download = admin_client.get(f"/tasks/{task_id}/attachments/{attachment_id}")
    assert download.status_code == 200
    assert download.content == b"hello"


def test_forbidden_without_permission(client: TestClient, admin_client: TestClient) -> None:
    # create a non-admin user without work perms
    created = admin_client.post(
        "/users",
        json={
            "email": "ops@karam-alarab.com",
            "password": "password-ops-1234",
            "roles": ["operations"],
        },
    )
    assert created.status_code == 201, created.text
    login_as(client, "ops@karam-alarab.com", "password-ops-1234")
    response = client.get("/task-types")
    assert response.status_code == 403


def test_illegal_entity_type(admin_client: TestClient) -> None:
    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    task_id = admin_client.post(
        "/tasks",
        json={"task_type_id": type_id, "title": "X"},
    ).json()["id"]
    response = admin_client.post(
        f"/tasks/{task_id}/entity-links",
        json={"entity_type": "invoice", "entity_id": "1"},
    )
    assert response.status_code == 400


def test_assign_creates_inbox_and_channel_deliveries(
    admin_client: TestClient, client: TestClient
) -> None:
    # employee user
    employee = admin_client.post(
        "/users",
        json={
            "email": "worker@karam-alarab.com",
            "password": "password-worker12",
            "roles": ["operations"],
        },
    )
    assert employee.status_code == 201, employee.text
    # grant work:read via superuser already not - register perms on operations
    admin_client.put(
        "/roles/operations/permissions",
        json={"permissions": ["work:read", "identity_access:read"]},
    )
    employee_id = employee.json()["id"]

    # two channels pointing at loopback (mocked)
    ch1 = admin_client.post(
        "/notification-channels",
        json={
            "name": "Email hub",
            "webhook_url": "http://127.0.0.1:9991/hook",
            "webhook_secret": "secret-email-hub-1",
        },
    )
    assert ch1.status_code == 201, ch1.text
    ch2 = admin_client.post(
        "/notification-channels",
        json={
            "name": "SMS hub",
            "webhook_url": "http://127.0.0.1:9992/hook",
            "webhook_secret": "secret-sms-hub-22",
        },
    )
    assert ch2.status_code == 201, ch2.text

    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    create = admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_id,
            "title": "Unload truck",
            "assignee_user_id": employee_id,
        },
    )
    assert create.status_code == 201, create.text
    task_id = create.json()["id"]

    login_as(client, "worker@karam-alarab.com", "password-worker12")
    inbox = client.get("/notifications")
    assert inbox.status_code == 200
    assert inbox.json()["total"] >= 1
    assert inbox.json()["data"][0]["taskId"] == task_id

    other = login_as(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    # admin may also have no notification for this assignment (recipient is worker)
    # worker cannot read admin's - already own inbox

    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http:
        processed = process_pending_deliveries(
            admin_client.app.state.session_factory,
            client=http,
            now=datetime.now(UTC),
        )
    assert processed >= 2
    assert len(seen) == 2
    bodies = [json.loads(r.content.decode()) for r in seen]
    names = {b["channel_name"] for b in bodies}
    assert names == {"Email hub", "SMS hub"}
    for body, req in zip(bodies, seen, strict=True):
        assert body["task_url"].endswith(f"/tasks/{task_id}")
        assert body["assignee_email"] == "worker@karam-alarab.com"
        assert verify_webhook_signature(
            secrets=["secret-email-hub-1", "secret-sms-hub-22"],
            event_id=req.headers["X-Karam-Event-Id"],
            timestamp=req.headers["X-Karam-Timestamp"],
            body=req.content,
            header=req.headers["X-Karam-Signature"],
        )


def test_webhook_500_still_keeps_task_and_inbox(admin_client: TestClient) -> None:
    employee = admin_client.post(
        "/users",
        json={
            "email": "worker2@karam-alarab.com",
            "password": "password-worker12",
            "roles": ["operations"],
        },
    ).json()
    admin_client.put(
        "/roles/operations/permissions",
        json={"permissions": ["work:read"]},
    )
    admin_client.post(
        "/notification-channels",
        json={
            "name": "Failing hub",
            "webhook_url": "http://127.0.0.1:9993/hook",
            "webhook_secret": "secret-failing-hub1",
        },
    )
    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    create = admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_id,
            "title": "Keep me",
            "assignee_user_id": employee["id"],
        },
    )
    assert create.status_code == 201

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="nope")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        process_pending_deliveries(
            admin_client.app.state.session_factory, client=http, now=datetime.now(UTC)
        )

    login_as(admin_client, "worker2@karam-alarab.com", "password-worker12")
    inbox = admin_client.get("/notifications")
    assert inbox.json()["total"] >= 1


def test_channel_crud_and_ssrf(admin_client: TestClient) -> None:
    bad = admin_client.post(
        "/notification-channels",
        json={
            "name": "Meta",
            "webhook_url": "http://169.254.169.254/latest",
            "webhook_secret": "secret-meta-data-12",
        },
    )
    assert bad.status_code == 400

    created = admin_client.post(
        "/notification-channels",
        json={
            "name": "Ops WhatsApp",
            "webhook_url": "http://127.0.0.1:9994/hook",
            "webhook_secret": "secret-whatsapp-hub",
        },
    )
    assert created.status_code == 201
    channel_id = created.json()["id"]
    assert "webhookSecret" in created.json()
    assert "…" in created.json()["webhookSecretMasked"] or "*" in created.json()[
        "webhookSecretMasked"
    ]

    patched = admin_client.patch(
        f"/notification-channels/{channel_id}",
        json={"name": "Ops SMS", "is_active": False},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Ops SMS"
    assert patched.json()["isActive"] is False

    rolled = admin_client.post(f"/notification-channels/{channel_id}/roll-secret")
    assert rolled.status_code == 200
    assert "webhookSecret" in rolled.json()

    deleted = admin_client.delete(f"/notification-channels/{channel_id}")
    assert deleted.status_code == 204


def test_create_without_assignee_no_notification(admin_client: TestClient) -> None:
    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    before = admin_client.get("/notifications").json()["total"]
    admin_client.post("/tasks", json={"task_type_id": type_id, "title": "Unassigned"})
    after = admin_client.get("/notifications").json()["total"]
    assert after == before


def test_notification_isolation(admin_client: TestClient, client: TestClient) -> None:
    worker = admin_client.post(
        "/users",
        json={
            "email": "iso@karam-alarab.com",
            "password": "password-worker12",
            "roles": ["operations"],
        },
    ).json()
    admin_client.put(
        "/roles/operations/permissions",
        json={"permissions": ["work:read"]},
    )
    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_id,
            "title": "Private",
            "assignee_user_id": worker["id"],
        },
    )
    login_as(client, "iso@karam-alarab.com", "password-worker12")
    note_id = client.get("/notifications").json()["data"][0]["id"]
    # admin cannot mark worker notification as read via worker id path when logged as admin
    login_as(admin_client, ADMIN_EMAIL, ADMIN_PASSWORD)
    # admin may have different inbox; marking worker's id should 403
    denied = admin_client.post(f"/notifications/{note_id}/read")
    assert denied.status_code == 403


def test_channel_410_deactivates(admin_client: TestClient) -> None:
    worker = admin_client.post(
        "/users",
        json={
            "email": "gone@karam-alarab.com",
            "password": "password-worker12",
            "roles": ["operations"],
        },
    ).json()
    ch = admin_client.post(
        "/notification-channels",
        json={
            "name": "Gone hub",
            "webhook_url": "http://127.0.0.1:9995/hook",
            "webhook_secret": "secret-gone-hub-123",
        },
    ).json()
    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_id,
            "title": "Gone",
            "assignee_user_id": worker["id"],
        },
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(410)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        process_pending_deliveries(
            admin_client.app.state.session_factory, client=http, now=datetime.now(UTC)
        )

    listed = admin_client.get(f"/notification-channels/{ch['id']}")
    assert listed.json()["isActive"] is False
