from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import sessionmaker

from database.models.work import NotificationChannelRow, WebhookDeliveryRow
from database.repositories.work_repository import SqlAlchemyWorkRepository
from domain.work.signing import sign_webhook_body

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 8
BACKOFF_SECONDS = (0, 10, 60, 300, 1800, 7200, 21600, 43200)


def process_pending_deliveries(
    session_factory: sessionmaker,
    *,
    client: httpx.Client | None = None,
    now: datetime | None = None,
    limit: int = 50,
) -> int:
    """Claim due deliveries and POST signed webhooks. Returns processed count."""
    moment = now or datetime.now(UTC)
    owns_client = client is None
    http = client or httpx.Client(timeout=5.0, follow_redirects=False)
    processed = 0
    try:
        session = session_factory()
        try:
            work = SqlAlchemyWorkRepository(session)
            deliveries = work.claim_due_deliveries(now=moment, limit=limit)
            for delivery in deliveries:
                channel = work.get_channel(delivery.channel_id)
                if channel is None or not channel.is_active:
                    delivery.status = "dead"
                    delivery.last_error = "Channel missing or inactive"
                    delivery.updated_at = moment
                    processed += 1
                    continue
                _attempt_one(http, delivery, channel, moment)
                processed += 1
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    finally:
        if owns_client:
            http.close()
    return processed


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
