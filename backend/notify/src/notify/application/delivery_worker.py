from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import sessionmaker

from notify.database.models.notify import NotificationChannelRow, WebhookDeliveryRow
from notify.database.repositories.notify_repository import SqlAlchemyNotifyRepository
from notify.domain.signing import sign_webhook_body
from support.tracing import TraceRecorder

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 8
BACKOFF_SECONDS = (0, 10, 60, 300, 1800, 7200, 21600, 43200)


def process_pending_deliveries(
    session_factory: sessionmaker,
    *,
    client: httpx.Client | None = None,
    now: datetime | None = None,
    limit: int = 50,
    trace_recorder: TraceRecorder | None = None,
) -> int:
    """Claim due deliveries and POST signed webhooks. Returns processed count."""
    moment = now or datetime.now(UTC)
    owns_client = client is None
    http = client or httpx.Client(timeout=5.0, follow_redirects=False)
    processed = 0
    # Buffer trace writes until after the worker session commits (SQLite lock safety).
    pending_traces: list[dict[str, Any]] = []
    try:
        session = session_factory()
        try:
            work = SqlAlchemyNotifyRepository(session)
            deliveries = work.claim_due_deliveries(now=moment, limit=limit)
            for delivery in deliveries:
                channel = work.get_channel(delivery.channel_id)
                if channel is None or not channel.is_active:
                    delivery.status = "dead"
                    delivery.last_error = "Channel missing or inactive"
                    delivery.updated_at = moment
                    pending_traces.append(
                        {
                            "delivery": delivery,
                            "status": "failed",
                            "summary": "Channel missing or inactive; delivery marked dead.",
                            "detail": {"deliveryId": str(delivery.id)},
                            "duration_ms": None,
                            "step_status": "failed",
                        }
                    )
                    processed += 1
                    continue
                started = time.perf_counter()
                _attempt_one(http, delivery, channel, moment)
                duration_ms = int((time.perf_counter() - started) * 1000)
                pending_traces.append(
                    {
                        "delivery": delivery,
                        "status": (
                            "succeeded"
                            if delivery.status == "succeeded"
                            else "failed"
                            if delivery.status in {"failed", "dead"}
                            else "partial"
                            if delivery.status == "retry"
                            else delivery.status
                        ),
                        "summary": _delivery_summary(delivery, channel.name),
                        "detail": {
                            "deliveryId": str(delivery.id),
                            "channelId": str(channel.id),
                            "channelName": channel.name,
                            "httpAttempts": delivery.attempts,
                            "deliveryStatus": delivery.status,
                            "lastError": delivery.last_error,
                        },
                        "duration_ms": duration_ms,
                        "step_status": (
                            "succeeded"
                            if delivery.status == "succeeded"
                            else "failed"
                            if delivery.status in {"failed", "dead"}
                            else "succeeded"  # retry scheduled is still a completed attempt step
                        ),
                    }
                )
                processed += 1
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        for item in pending_traces:
            _trace_delivery(
                trace_recorder,
                item["delivery"],
                status=item["status"],
                summary=item["summary"],
                detail=item["detail"],
                duration_ms=item["duration_ms"],
                step_status=item["step_status"],
            )
    finally:
        if owns_client:
            http.close()
    return processed


def _delivery_summary(delivery: WebhookDeliveryRow, channel_name: str) -> str:
    """Human-readable webhook attempt outcome."""
    if delivery.status == "succeeded":
        return f"Webhook post to “{channel_name}” succeeded."
    if delivery.status == "retry":
        return (
            f"Webhook post to “{channel_name}” failed "
            f"({delivery.last_error or 'error'}); will retry."
        )
    if delivery.status == "dead":
        return f"Webhook post to “{channel_name}” stopped ({delivery.last_error or 'dead'})."
    return f"Webhook post to “{channel_name}” failed ({delivery.last_error or 'error'})."


def _trace_delivery(
    trace_recorder: TraceRecorder | None,
    delivery: WebhookDeliveryRow,
    *,
    status: str,
    summary: str,
    detail: dict[str, Any],
    duration_ms: int | None = None,
    step_status: str | None = None,
) -> None:
    """Append a webhook_post step onto the correlation journey (new or existing)."""
    if trace_recorder is None:
        return
    correlation_id = str(delivery.event_id)
    # Find an open work trace by starting a sibling step via a lightweight follow-up
    # trace under the same correlation (keeps async deliveries on the same id).
    trace_id = trace_recorder.start(
        context="work",
        operation="webhook_delivery",
        correlation_id=correlation_id,
        entity_type="webhook_delivery",
        entity_id=str(delivery.id),
        summary=summary,
    )
    trace_recorder.step(
        trace_id,
        step_key="webhook_post",
        status=step_status or status,
        summary=summary,
        detail=detail,
        duration_ms=duration_ms,
    )
    if delivery.status == "succeeded":
        trace_recorder.succeed(trace_id, summary=summary)
    elif delivery.status in {"failed", "dead"}:
        trace_recorder.fail(
            trace_id,
            summary=summary,
            error_message=delivery.last_error or summary,
        )
    else:
        trace_recorder.partial(
            trace_id,
            summary=summary,
            error_message=delivery.last_error,
        )


def _attempt_one(
    http: httpx.Client,
    delivery: WebhookDeliveryRow,
    channel: NotificationChannelRow,
    now: datetime,
) -> None:
    """POST one delivery; update status/backoff or deactivate on 410."""
    body = delivery.payload_json.encode("utf-8")
    event_id = str(delivery.event_id)
    timestamp = str(int(now.timestamp()))
    signature = sign_webhook_body(
        secret=channel.webhook_secret,
        event_id=event_id,
        timestamp=timestamp,
        body=body,
    )
    headers = {
        "Content-Type": "application/json",
        "X-Karam-Event-Id": event_id,
        "X-Karam-Timestamp": timestamp,
        "X-Karam-Signature": signature,
    }
    delivery.attempts += 1
    delivery.status = "in_flight"
    delivery.updated_at = now
    try:
        response = http.post(channel.webhook_url, content=body, headers=headers)
    except httpx.HTTPError as exc:
        _schedule_retry(delivery, now, error=str(exc))
        return

    if 200 <= response.status_code < 300:
        delivery.status = "succeeded"
        delivery.last_error = None
        return

    if response.status_code == 410:
        channel.is_active = False
        channel.disabled_reason = "Remote returned 410 Gone"
        channel.updated_at = now
        delivery.status = "dead"
        delivery.last_error = "410 Gone"
        return

    if response.status_code in {400, 401, 403, 404, 422}:
        delivery.status = "failed"
        delivery.last_error = f"HTTP {response.status_code}"
        return

    retry_after = response.headers.get("Retry-After")
    extra = None
    if response.status_code == 429 and retry_after and retry_after.isdigit():
        extra = int(retry_after)
    _schedule_retry(
        delivery,
        now,
        error=f"HTTP {response.status_code}",
        retry_after_seconds=extra,
    )


def _schedule_retry(
    delivery: WebhookDeliveryRow,
    now: datetime,
    *,
    error: str,
    retry_after_seconds: int | None = None,
) -> None:
    """Mark retry or dead when max attempts reached."""
    delivery.last_error = error
    if delivery.attempts >= MAX_ATTEMPTS:
        delivery.status = "dead"
        return
    idx = min(delivery.attempts, len(BACKOFF_SECONDS) - 1)
    delay = retry_after_seconds if retry_after_seconds is not None else BACKOFF_SECONDS[idx]
    delivery.status = "retry"
    delivery.next_attempt_at = now + timedelta(seconds=delay)


def active_secrets_for_channel(channel: NotificationChannelRow, now: datetime) -> list[str]:
    """Current secret plus previous during roll overlap."""
    secrets = [channel.webhook_secret]
    if (
        channel.previous_secret
        and channel.previous_secret_expires_at
        and channel.previous_secret_expires_at > now
    ):
        secrets.append(channel.previous_secret)
    return secrets


def parse_payload(delivery: WebhookDeliveryRow) -> dict[str, Any]:
    """Decode delivery JSON payload."""
    return json.loads(delivery.payload_json)
