from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from database.models.identity import LoginAttemptRow


class SqlAlchemyLoginAttemptStore:
    """Store failed logins for rate limiting."""

    def __init__(self, session: Session) -> None:
        """Bind this adapter to the request DB session."""
        self._session = session

    def record_failure(self, key: str, *, now: datetime) -> int:
        """Record a failed attempt; return recent count from now."""
        self._session.add(LoginAttemptRow(attempt_key=key, attempted_at=now))
        self._session.flush()
        return self.recent_failures(key, since=now)

    def clear(self, key: str) -> None:
        """Clear failures after a successful login."""
        self._session.execute(
            delete(LoginAttemptRow).where(LoginAttemptRow.attempt_key == key)
        )
        self._session.flush()

    def recent_failures(self, key: str, *, since: datetime) -> int:
        """Count failures for a key since a timestamp."""
        count = self._session.scalar(
            select(func.count())
            .select_from(LoginAttemptRow)
            .where(
                LoginAttemptRow.attempt_key == key,
                LoginAttemptRow.attempted_at >= since,
            )
        )
        return int(count or 0)
