from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from application.delivery_worker import process_pending_deliveries
from domain.work.events import TaskAssigned
from helpers import login_as


def _workflow_and_type(admin_client: TestClient) -> str:
    wf = admin_client.post(
        "/workflows",
        json={
            "name": f"trace-wf-{uuid4().hex[:8]}",
            "statuses": [
                {"key": "todo", "name": "To do", "is_initial": True},
                {"key": "done", "name": "Done", "is_initial": False},
            ],
            "transitions": [
                {"from_status_key": "todo", "to_status_key": "done", "name": "finish"}
            ],
        },
    )
    assert wf.status_code == 201, wf.text
    tt = admin_client.post(
        "/task-types",
        json={
            "key": f"trace_type_{uuid4().hex[:8]}",
            "name": "Trace type",
            "workflow_id": wf.json()["id"],
        },
    )
    assert tt.status_code == 201, tt.text
    return tt.json()["id"]


def test_assign_creates_readable_process_trace(admin_client: TestClient) -> None:
    worker = admin_client.post(
        "/users",
        json={
            "email": f"trace-{uuid4().hex[:6]}@karam-alarab.com",
            "password": "password-worker12",
            "roles": ["operations"],
        },
    ).json()
    admin_client.post(
        "/notification-channels",
        json={
            "name": f"Trace hub {uuid4().hex[:6]}",
            "webhook_url": "http://127.0.0.1:9910/hook",
            "webhook_secret": "secret-trace-hub-12",
        },
    )
    type_id = _workflow_and_type(admin_client)
    created = admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_id,
            "title": "Trace me",
            "assignee_user_id": worker["id"],
        },
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]

    listed = admin_client.get(
        "/process-traces",
        params={"context": "work", "entityId": task_id},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] >= 1
    trace = listed.json()["data"][0]
    assert trace["summary"]
    assert trace["status"] == "succeeded"
    correlation_id = trace["correlationId"]

    by_corr = admin_client.get(f"/process-traces/by-correlation/{correlation_id}")
    assert by_corr.status_code == 200
    journeys = by_corr.json()["traces"]
    assert journeys
    steps = journeys[0]["steps"]
    keys = [s["stepKey"] for s in steps]
    assert "start" in keys
    assert "enqueue_inbox" in keys
    assert "enqueue_delivery" in keys
    assert all(s["summary"] for s in steps)


def test_process_traces_forbidden_without_permission(
    client: TestClient, admin_client: TestClient
) -> None:
    admin_client.post(
        "/users",
        json={
            "email": "no-trace@karam-alarab.com",
            "password": "password-worker12",
            "roles": ["operations"],
        },
    )
    login_as(client, "no-trace@karam-alarab.com", "password-worker12")
    response = client.get("/process-traces")
    assert response.status_code == 403
    assert "permission" in response.json()["error"]["message"].lower()


def test_enqueue_failure_leaves_failed_trace(
    admin_client: TestClient, monkeypatch
) -> None:
    worker = admin_client.post(
        "/users",
        json={
            "email": f"fail-{uuid4().hex[:6]}@karam-alarab.com",
            "password": "password-worker12",
            "roles": ["operations"],
        },
    ).json()
    type_id = _workflow_and_type(admin_client)

    def boom(_event: object) -> None:
        raise RuntimeError("simulated enqueue crash")

    # EventBus holds a bound method; replace that subscription, not the class.
    bus = admin_client.app.state.event_bus
    monkeypatch.setitem(bus._handlers, TaskAssigned, [boom])

    created = admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_id,
            "title": "Still created",
            "assignee_user_id": worker["id"],
        },
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]

    # EventBus records support/event_handler failure
    listed = admin_client.get(
        "/process-traces",
        params={"context": "support", "operation": "event_handler"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    failed = listed.json()["data"][0]
    assert failed["status"] == "failed"
    assert "failed" in failed["summary"].lower()
    assert failed["errorMessage"]
    assert "RuntimeError" in failed["errorMessage"]

    # Task still exists
    assert admin_client.get(f"/tasks/{task_id}").status_code == 200


def test_mid_enqueue_failure_marks_assign_notify_failed(
    admin_client: TestClient, monkeypatch
) -> None:
    from database.repositories.work_repository import SqlAlchemyWorkRepository

    worker = admin_client.post(
        "/users",
        json={
            "email": f"mid-{uuid4().hex[:6]}@karam-alarab.com",
            "password": "password-worker12",
            "roles": ["operations"],
        },
    ).json()
    type_id = _workflow_and_type(admin_client)

    def boom_inbox(self, *args, **kwargs):  # noqa: ANN001
        raise RuntimeError("simulated inbox write failure")

    monkeypatch.setattr(SqlAlchemyWorkRepository, "create_notification", boom_inbox)

    created = admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_id,
            "title": "Mid-fail notify",
            "assignee_user_id": worker["id"],
        },
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]

    listed = admin_client.get(
        "/process-traces",
        params={"context": "work", "operation": "task_assign_notify", "entityId": task_id},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] >= 1
    failed = listed.json()["data"][0]
    assert failed["status"] == "failed"
    assert "enqueue" in failed["summary"].lower() or "failed" in failed["summary"].lower()
    assert failed["errorMessage"]
    assert "RuntimeError" in failed["errorMessage"]
    assert failed["correlationId"]
    assert failed["requestId"]

    by_corr = admin_client.get(
        f"/process-traces/by-correlation/{failed['correlationId']}"
    )
    steps = by_corr.json()["traces"][0]["steps"]
    keys = [s["stepKey"] for s in steps]
    assert "start" in keys
    assert "enqueue_failed" in keys
    assert any(s["summary"] for s in steps)


def test_webhook_retry_visible_and_process_deliveries(
    admin_client: TestClient,
) -> None:
    worker = admin_client.post(
        "/users",
        json={
            "email": f"wh-{uuid4().hex[:6]}@karam-alarab.com",
            "password": "password-worker12",
            "roles": ["operations"],
        },
    ).json()
    admin_client.post(
        "/notification-channels",
        json={
            "name": f"Retry hub {uuid4().hex[:6]}",
            "webhook_url": "http://127.0.0.1:9911/hook",
            "webhook_secret": "secret-retry-hub-12",
        },
    )
    type_id = _workflow_and_type(admin_client)
    created = admin_client.post(
        "/tasks",
        json={
            "task_type_id": type_id,
            "title": "Webhook retry",
            "assignee_user_id": worker["id"],
        },
    )
    assert created.status_code == 201
    corr = admin_client.get(
        "/process-traces",
        params={"entityId": created.json()["id"], "context": "work"},
    ).json()["data"][0]["correlationId"]

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="down")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        process_pending_deliveries(
            admin_client.app.state.session_factory,
            client=http,
            now=datetime.now(UTC),
            trace_recorder=admin_client.app.state.trace_recorder,
        )

    by_corr = admin_client.get(f"/process-traces/by-correlation/{corr}")
    ops = {t["operation"] for t in by_corr.json()["traces"]}
    assert "webhook_delivery" in ops
    webhook_trace = next(
        t for t in by_corr.json()["traces"] if t["operation"] == "webhook_delivery"
    )
    assert webhook_trace["status"] in {"partial", "failed"}
    assert any(s["stepKey"] == "webhook_post" for s in webhook_trace["steps"])

    pumped = admin_client.post("/work/process-deliveries")
    assert pumped.status_code == 200
    assert "processed" in pumped.json()


def test_process_deliveries_blocked_in_production(
    admin_client: TestClient, monkeypatch
) -> None:
    settings = admin_client.app.state.settings
    monkeypatch.setattr(settings, "environment", "production")
    response = admin_client.post("/work/process-deliveries")
    assert response.status_code == 403
    assert "production" in response.json()["error"]["message"].lower()
