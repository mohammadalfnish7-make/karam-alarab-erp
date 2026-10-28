from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from api.deps import get_channel_service, require_permission
from api.work_dto import CreateChannelRequest, PatchChannelRequest
from application.actor import Actor
from application.channel_service import ChannelService

router = APIRouter(tags=["notification-channels"])


def _channel_json(row: dict[str, Any]) -> dict[str, Any]:
    """Serialize channel for HTTP (camelCase)."""
    out: dict[str, Any] = {
        "id": str(row["id"]),
        "name": row["name"],
        "webhookUrl": row["webhook_url"],
        "webhookSecretMasked": row["webhook_secret_masked"],
        "isActive": row["is_active"],
        "disabledReason": row["disabled_reason"],
    }
    if "webhook_secret" in row:
        out["webhookSecret"] = row["webhook_secret"]
    return out


@router.post("/notification-channels", status_code=201)
def create_channel(
    body: CreateChannelRequest,
    _: Annotated[Actor, Depends(require_permission("work:admin"))],
    channels: Annotated[ChannelService, Depends(get_channel_service)],
) -> dict[str, Any]:
    """Admin: add a named webhook channel."""
    return _channel_json(
        channels.create(
            name=body.name,
            webhook_url=body.webhook_url,
            webhook_secret=body.webhook_secret,
        )
    )


@router.get("/notification-channels")
def list_channels(
    _: Annotated[Actor, Depends(require_permission("work:admin"))],
    channels: Annotated[ChannelService, Depends(get_channel_service)],
) -> list[dict[str, Any]]:
    """Admin: list channels."""
    return [_channel_json(c) for c in channels.list_channels()]


@router.get("/notification-channels/{channel_id}")
def get_channel(
    channel_id: UUID,
    _: Annotated[Actor, Depends(require_permission("work:admin"))],
    channels: Annotated[ChannelService, Depends(get_channel_service)],
) -> dict[str, Any]:
    """Admin: get one channel."""
    return _channel_json(channels.get(channel_id))


@router.patch("/notification-channels/{channel_id}")
def patch_channel(
    channel_id: UUID,
    body: PatchChannelRequest,
    _: Annotated[Actor, Depends(require_permission("work:admin"))],
    channels: Annotated[ChannelService, Depends(get_channel_service)],
) -> dict[str, Any]:
    """Admin: edit name, webhook, secret, or active flag."""
    return _channel_json(
        channels.update(
            channel_id,
            name=body.name,
            webhook_url=body.webhook_url,
            webhook_secret=body.webhook_secret,
            is_active=body.is_active,
        )
    )


@router.post("/notification-channels/{channel_id}/roll-secret", status_code=200)
def roll_secret(
    channel_id: UUID,
    _: Annotated[Actor, Depends(require_permission("work:admin"))],
    channels: Annotated[ChannelService, Depends(get_channel_service)],
) -> dict[str, Any]:
    """Admin: rotate signing secret with overlap window."""
    return _channel_json(channels.roll_secret(channel_id))


@router.delete("/notification-channels/{channel_id}", status_code=204)
def delete_channel(
    channel_id: UUID,
    _: Annotated[Actor, Depends(require_permission("work:admin"))],
    channels: Annotated[ChannelService, Depends(get_channel_service)],
) -> Response:
    """Admin: remove a channel."""
    channels.delete(channel_id)
    return Response(status_code=204)
