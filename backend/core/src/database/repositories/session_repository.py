from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database.models.identity import SessionRow
from domain.shared.user_id import UserId


class SqlAlchemySessionRepository:
    """Persist hashed session cookies."""

    def __init__(self, session: Session) -> None:
        """Bind this adapter to the request DB session."""
        self._session = session

    def create(
        self,
        *,
        user_id: UserId,
        token_hash: str,
        expires_at: datetime,
        created_at: datetime,
    ) -> UUID:
        """Create a session row; return its id."""
        session_id = uuid4()
        self._session.add(
            SessionRow(
                id=session_id,
                user_id=user_id.value,
                token_hash=token_hash,
                expires_at=expires_at,
                created_at=created_at,
            )
        )
        self._session.flush()
        return session_id

    def get_by_token_hash(
        self,
        token_hash: str,
    ) -> tuple[UUID, UserId, datetime] | None:
        """Find session by hashed token."""
        row = self._session.scalar(
            select(SessionRow).where(SessionRow.token_hash == token_hash)
        )
        if row is None:
            return None
        return row.id, UserId(row.user_id), row.expires_at

    def delete(self, session_id: UUID) -> None:
        """Delete one session by id."""
        self._session.execute(delete(SessionRow).where(SessionRow.id == session_id))
        self._session.flush()

    def delete_by_token_hash(self, token_hash: str) -> None:
        """Delete the session for this hashed cookie."""
        self._session.execute(
            delete(SessionRow).where(SessionRow.token_hash == token_hash)
        )
        self._session.flush()

    def delete_all_for_user(self, user_id: UserId) -> None:
        """Revoke every session for a user."""
        self._session.execute(
            delete(SessionRow).where(SessionRow.user_id == user_id.value)
        )
        self._session.flush()
