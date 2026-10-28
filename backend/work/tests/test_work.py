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


def _create_type(
    admin_client: TestClient,
    workflow_id: str,
    key: str | None = None,
    *,
    name: str = "Ops item",
) -> str:
    response = admin_client.post(
        "/task-types",
        json={
            "key": key or f"type_{uuid4().hex[:8]}",
            "name": name,
            "workflow_id": workflow_id,
            "hierarchy_level": "standard",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_list_tasks_all_and_filters(admin_client: TestClient) -> None:
    workflow_id = _create_workflow(admin_client)
    type_a = _create_type(admin_client, workflow_id, name="Type A")
    type_b = _create_type(admin_client, workflow_id, key=f"type_b_{uuid4().hex[:6]}", name="Type B")
    a1 = admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_a,
            "title": "A due",
            "due_on": "2026-11-01",
            "priority": "high",
        },
    )
    b1 = admin_client.post(
        "/tasks",
        json={"task_type_id": type_b, "title": "B other", "priority": "low"},
    )
    assert a1.status_code == 201 and b1.status_code == 201

    all_tasks = admin_client.get("/tasks", params={"pageSize": 100})
    assert all_tasks.status_code == 200
    ids = {row["id"] for row in all_tasks.json()["data"]}
    assert a1.json()["id"] in ids
    assert b1.json()["id"] in ids

    by_type = admin_client.get("/tasks", params={"taskTypeId": type_a, "pageSize": 100})
    assert {row["id"] for row in by_type.json()["data"]} == {a1.json()["id"]}

    by_due = admin_client.get(
        "/tasks",
        params={"dueOnFrom": "2026-11-01", "dueOnTo": "2026-11-01", "pageSize": 100},
    )
    assert a1.json()["id"] in {row["id"] for row in by_due.json()["data"]}
    assert b1.json()["id"] not in {row["id"] for row in by_due.json()["data"]}

    by_priority = admin_client.get("/tasks", params={"priority": "high", "pageSize": 100})
    assert a1.json()["id"] in {row["id"] for row in by_priority.json()["data"]}

    by_q = admin_client.get("/tasks", params={"q": "A due", "pageSize": 100})
    assert a1.json()["id"] in {row["id"] for row in by_q.json()["data"]}
    assert b1.json()["id"] not in {row["id"] for row in by_q.json()["data"]}


def test_task_reference_is_type_name_plus_sequence(admin_client: TestClient) -> None:
    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id, name="collecting payment")
    first = admin_client.post(
        "/tasks",
        json={"task_type_id": type_id, "title": "Invoice A"},
    )
    second = admin_client.post(
        "/tasks",
        json={"task_type_id": type_id, "title": "Invoice B"},
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["reference"] == "collecting payment-1"
    assert first.json()["sequenceNumber"] == 1
    assert second.json()["reference"] == "collecting payment-2"
    assert second.json()["sequenceNumber"] == 2


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
    renamed = admin_client.put(
        f"/tasks/{task_id}/steps/{step_id}",
        json={"title": "Check seal again"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["steps"][0]["title"] == "Check seal again"
    deleted = admin_client.delete(f"/tasks/{task_id}/steps/{step_id}")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["steps"] == []

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
    removed_att = admin_client.delete(
        f"/tasks/{task_id}/attachments/{attachment_id}"
    )
    assert removed_att.status_code == 200, removed_att.text
    assert removed_att.json()["attachments"] == []
    gone = admin_client.get(f"/tasks/{task_id}/attachments/{attachment_id}")
    assert gone.status_code == 404


def test_forbidden_without_permission(client: TestClient, admin_client: TestClient) -> None:
    # Seeded sales includes work:read; strip it so this user has no work access.
    cleared = admin_client.put("/roles/sales/permissions", json={"permissions": []})
    assert cleared.status_code == 204, cleared.text
    email = f"noperm.{uuid4().hex[:8]}@karam-alarab.com"
    created = admin_client.post(
        "/users",
        json={
            "email": email,
            "password": "password-ops-1234",
            "roles": ["sales"],
        },
    )
    assert created.status_code == 201, created.text
    login_as(client, email, "password-ops-1234")
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


def test_list_task_assignees(admin_client: TestClient) -> None:
    response = admin_client.get("/task-assignees")
    assert response.status_code == 200, response.text
    emails = {row["email"] for row in response.json()}
    assert ADMIN_EMAIL in emails


def test_due_on_and_priority_round_trip(admin_client: TestClient) -> None:
    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    create = admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_id,
            "title": "Due cargo",
            "due_on": "2026-11-05",
            "priority": "high",
        },
    )
    assert create.status_code == 201, create.text
    task = create.json()
    assert task["dueOn"] == "2026-11-05"
    assert task["priority"] == "high"
    task_id = task["id"]

    patched = admin_client.patch(
        f"/tasks/{task_id}",
        json={"due_on": "2026-11-10", "priority": "urgent"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["dueOn"] == "2026-11-10"
    assert patched.json()["priority"] == "urgent"

    cleared = admin_client.patch(f"/tasks/{task_id}", json={"due_on": None})
    assert cleared.status_code == 200
    assert cleared.json()["dueOn"] is None


def test_task_writes_appear_on_audit_entries(admin_client: TestClient) -> None:
    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    create = admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_id,
            "title": "Audit me",
            "priority": "low",
            "due_on": "2026-12-01",
        },
    )
    assert create.status_code == 201, create.text
    task_id = create.json()["id"]

    moved = admin_client.post(
        f"/tasks/{task_id}/transitions",
        json={"to_status_key": "doing"},
    )
    assert moved.status_code == 200

    audit = admin_client.get(f"/audit-entries?entity=task&entityId={task_id}")
    assert audit.status_code == 200, audit.text
    actions = {row["action"] for row in audit.json()["data"]}
    assert "TaskCreated" in actions
    assert "TaskStatusChanged" in actions

    missing = admin_client.get("/audit-entries?entity=task")
    assert missing.status_code in {400, 422}


def test_stored_file_entity_link(admin_client: TestClient) -> None:
    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    task_id = admin_client.post(
        "/tasks",
        json={"task_type_id": type_id, "title": "With file"},
    ).json()["id"]
    uploaded = admin_client.post(
        "/files",
        files={"file": ("invoice-12.pdf", b"%PDF-1.4 invoice", "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    file_id = uploaded.json()["id"]
    linked = admin_client.post(
        f"/tasks/{task_id}/entity-links",
        json={"entity_type": "stored_file", "entity_id": file_id},
    )
    assert linked.status_code == 201, linked.text
    assert any(
        e["entityType"] == "stored_file" and e["entityId"] == file_id
        for e in linked.json()["entityLinks"]
    )
    unlinked = admin_client.delete(
        f"/tasks/{task_id}/entity-links/stored_file/{file_id}"
    )
    assert unlinked.status_code == 200, unlinked.text
    assert unlinked.json()["entityLinks"] == []
    missing = admin_client.delete(
        f"/tasks/{task_id}/entity-links/stored_file/{file_id}"
    )
    assert missing.status_code == 400
    audit = admin_client.get(f"/audit-entries?entity=task&entityId={task_id}")
    assert audit.status_code == 200, audit.text
    summaries = [row["summary"] for row in audit.json()["data"]]
    assert any("Linked file “invoice-12.pdf”" in s for s in summaries)
    assert any("Unlinked file “invoice-12.pdf”" in s for s in summaries)


def test_only_creator_can_manage_steps(
    admin_client: TestClient, client: TestClient
) -> None:
    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    worker = admin_client.post(
        "/users",
        json={
            "email": f"stepper.{uuid4().hex[:8]}@karam-alarab.com",
            "password": "password-stepper12",
            "roles": ["operations"],
        },
    )
    assert worker.status_code == 201, worker.text
    worker_id = worker.json()["id"]
    create = admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_id,
            "title": "Creator owns steps",
            "assignee_user_id": worker_id,
        },
    )
    assert create.status_code == 201, create.text
    task_id = create.json()["id"]
    step_id = admin_client.post(
        f"/tasks/{task_id}/steps",
        json={"title": "Creator step"},
    ).json()["steps"][0]["id"]

    login_as(client, worker.json()["email"], "password-stepper12")
    denied_add = client.post(f"/tasks/{task_id}/steps", json={"title": "Nope"})
    assert denied_add.status_code == 403
    denied_rename = client.put(
        f"/tasks/{task_id}/steps/{step_id}",
        json={"title": "Hijack"},
    )
    assert denied_rename.status_code == 403
    denied_delete = client.delete(f"/tasks/{task_id}/steps/{step_id}")
    assert denied_delete.status_code == 403
    # Assignee can still complete the step.
    done = client.patch(
        f"/tasks/{task_id}/steps/{step_id}",
        json={"is_done": True},
    )
    assert done.status_code == 200, done.text
    assert done.json()["steps"][0]["isDone"] is True


def test_follower_can_remind_assignee(admin_client: TestClient, client: TestClient) -> None:
    follower = admin_client.post(
        "/users",
        json={
            "email": f"follower.{uuid4().hex[:8]}@karam-alarab.com",
            "password": "password-follower1",
            "roles": ["operations"],
        },
    )
    assert follower.status_code == 201, follower.text
    follower_id = follower.json()["id"]
    follower_email = follower.json()["email"]

    workflow_id = _create_workflow(admin_client)
    type_id = _create_type(admin_client, workflow_id)
    me = admin_client.get("/users/me").json()
    create = admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_id,
            "title": "Need reminder",
            "assignee_user_id": me["id"],
            "follower_user_ids": [follower_id],
        },
    )
    assert create.status_code == 201, create.text
    task = create.json()
    assert follower_id in task["followerUserIds"]
    task_id = task["id"]

    login_as(client, follower_email, "password-follower1")
    reminded = client.post(
        f"/tasks/{task_id}/reminders",
        json={"message": "Please collect today"},
    )
    assert reminded.status_code == 200, reminded.text

    login_as(admin_client, ADMIN_EMAIL, ADMIN_PASSWORD)
    inbox = admin_client.get("/notifications").json()
    assert any(
        n.get("kind") == "task_reminder" or "Reminder" in n.get("title", "")
        for n in inbox["data"]
    )
