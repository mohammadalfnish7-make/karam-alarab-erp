from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Time source so tests can freeze 'now'."""

    def now(self) -> datetime:
        """Return current UTC time."""
        ...


class SystemClock:
    """Real wall-clock time in UTC."""

    def now(self) -> datetime:
        """Return current UTC time."""
        return datetime.now(UTC)
