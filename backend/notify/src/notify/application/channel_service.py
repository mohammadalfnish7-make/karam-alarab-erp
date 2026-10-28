from __future__ import annotations

import secrets
from datetime import timedelta
from uuid import UUID

from config.settings import Settings
from notify.database.repositories.notify_repository import SqlAlchemyNotifyRepository
from domain.shared.clock import Clock
from domain.shared.domain_error import ConflictError, NotFoundError, ValidationError
from notify.domain.webhook_url import validate_webhook_url
from support.events import UnitOfWork

SECRET_ROLL_OVERLAP = timedelta(hours=24)


class ChannelService:
    """Admin CRUD for notification channels (name + webhook)."""

    def __init__(
        self,
        *,
        work: SqlAlchemyNotifyRepository,
        clock: Clock,
        uow: UnitOfWork,
        settings: Settings,
    ) -> None:
        """Wire repository, clock, UoW, and settings for SSRF rules."""
        self._work = work
        self._clock = clock
        self._uow = uow
        self._settings = settings

    def create(self, *, name: str, webhook_url: str, webhook_secret: str | None = None) -> dict:
        """Create an active channel with a unique name."""
        cleaned = name.strip()
        if not cleaned:
            raise ValidationError(
                "Name is required.", fields={"name": "Name is required."}
            )
        if self._work.get_channel_by_name(cleaned) is not None:
            raise ConflictError("A notification channel with this name already exists.")
        url = validate_webhook_url(
            webhook_url, allow_http_loopback=not self._settings.is_production
        )
        secret = webhook_secret.strip() if webhook_secret else secrets.token_urlsafe(32)
        if len(secret) < 16:
            raise ValidationError(
                "Webhook secret must be at least 16 characters.",
                fields={"webhook_secret": "Webhook secret must be at least 16 characters."},
            )
        now = self._clock.now()
        row = self._work.create_channel(
            name=cleaned, webhook_url=url, webhook_secret=secret, now=now
        )
        self._uow.commit()
        return self._public(row, include_secret=True)

    def list_channels(self) -> list[dict]:
        """List channels with masked secrets."""
        return [self._public(r) for r in self._work.list_channels()]

    def get(self, channel_id: UUID) -> dict:
        """Get one channel (secret masked)."""
        row = self._work.get_channel(channel_id)
        if row is None:
            raise NotFoundError("Channel not found.")
        return self._public(row)

    def update(
        self,
        channel_id: UUID,
        *,
        name: str | None = None,
        webhook_url: str | None = None,
        webhook_secret: str | None = None,
        is_active: bool | None = None,
    ) -> dict:
        """Patch channel fields."""
        row = self._work.get_channel(channel_id)
        if row is None:
            raise NotFoundError("Channel not found.")
        if name is not None:
            cleaned = name.strip()
            if not cleaned:
                raise ValidationError(
                    "Name is required.", fields={"name": "Name is required."}
                )
            other = self._work.get_channel_by_name(cleaned)
            if other is not None and other.id != channel_id:
                raise ConflictError(
                    "A notification channel with this name already exists."
                )
            row.name = cleaned
        if webhook_url is not None:
            row.webhook_url = validate_webhook_url(
                webhook_url, allow_http_loopback=not self._settings.is_production
            )
        if webhook_secret is not None:
            secret = webhook_secret.strip()
            if len(secret) < 16:
                raise ValidationError(
                    "Webhook secret must be at least 16 characters.",
                    fields={"webhook_secret": "Webhook secret must be at least 16 characters."},
                )
            row.webhook_secret = secret
            row.previous_secret = None
            row.previous_secret_expires_at = None
        if is_active is not None:
            row.is_active = is_active
            if is_active:
                row.disabled_reason = None
        row.updated_at = self._clock.now()
        self._work.save_channel(row)
        self._uow.commit()
        return self._public(row)

    def roll_secret(self, channel_id: UUID) -> dict:
        """Rotate secret; keep previous valid for 24h overlap."""
        row = self._work.get_channel(channel_id)
        if row is None:
            raise NotFoundError("Channel not found.")
        now = self._clock.now()
        row.previous_secret = row.webhook_secret
        row.previous_secret_expires_at = now + SECRET_ROLL_OVERLAP
        new_secret = secrets.token_urlsafe(32)
        row.webhook_secret = new_secret
        row.updated_at = now
        self._work.save_channel(row)
        self._uow.commit()
        return self._public(row, include_secret=True)

    def delete(self, channel_id: UUID) -> None:
        """Hard-delete a channel."""
        if self._work.get_channel(channel_id) is None:
            raise NotFoundError("Channel not found.")
        self._work.delete_channel(channel_id)
        self._uow.commit()

    @staticmethod
    def _public(row, *, include_secret: bool = False) -> dict:  # noqa: ANN001
        data = {
            "id": row.id,
            "name": row.name,
            "webhook_url": row.webhook_url,
            "webhook_secret_masked": _mask(row.webhook_secret),
            "is_active": row.is_active,
            "disabled_reason": row.disabled_reason,
        }
        if include_secret:
            data["webhook_secret"] = row.webhook_secret
        return data


def _mask(secret: str) -> str:
    if len(secret) <= 8:
        return "********"
    return secret[:4] + "…" + secret[-4:]
