from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ForbidModel(BaseModel):
    """Reject unknown fields."""

    model_config = ConfigDict(extra="forbid")


class CreateChannelRequest(ForbidModel):
    """Admin: create a notification channel."""

    name: str = Field(min_length=1, max_length=128)
    webhook_url: str = Field(min_length=1, max_length=2048)
    webhook_secret: str | None = Field(default=None, min_length=16, max_length=255)


class PatchChannelRequest(ForbidModel):
    """Admin: update a notification channel."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    webhook_url: str | None = Field(default=None, min_length=1, max_length=2048)
    webhook_secret: str | None = Field(default=None, min_length=16, max_length=255)
    is_active: bool | None = None
