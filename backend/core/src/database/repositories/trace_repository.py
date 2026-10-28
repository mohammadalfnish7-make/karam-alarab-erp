from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from database.models.trace import ProcessTraceRow, ProcessTraceStepRow


class SqlAlchemyTraceRepository:
    """Persist and query core process traces for all bounded contexts."""

    def __init__(self, session: Session) -> None:
        """Bind to a short-lived or request DB session."""
        self._session = session

    def create_trace(
        self,
        *,
        correlation_id: str,
        request_id: str,
        context: str,
        operation: str,
        entity_type: str,
        entity_id: str,
        summary: str,
        now: datetime,
    ) -> ProcessTraceRow:
        """Insert a running process trace."""
        row = ProcessTraceRow(
            id=uuid4(),
            correlation_id=correlation_id,
            request_id=request_id or "-",
            context=context,
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            status="running",
            summary=summary,
            error_message=None,
            created_at=now,
            finished_at=None,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def add_step(
        self,
        *,
        trace_id: UUID,
        step_key: str,
        status: str,
        summary: str,
        detail: dict | None,
        duration_ms: int | None,
        now: datetime,
    ) -> ProcessTraceStepRow:
        """Append an ordered stage step."""
        position = int(
            self._session.scalar(
                select(func.count())
                .select_from(ProcessTraceStepRow)
                .where(ProcessTraceStepRow.trace_id == trace_id)
            )
            or 0
        )
        row = ProcessTraceStepRow(
            id=uuid4(),
            trace_id=trace_id,
            position=position,
            step_key=step_key,
            status=status,
            summary=summary,
            detail_json=json.dumps(detail or {}, default=str)[:4000],
            duration_ms=duration_ms,
            created_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def finish_trace(
        self,
        trace_id: UUID,
        *,
        status: str,
        summary: str,
        error_message: str | None,
        now: datetime,
    ) -> ProcessTraceRow | None:
        """Mark a trace finished with a human summary."""
        row = self._session.get(ProcessTraceRow, trace_id)
        if row is None:
            return None
        row.status = status
        row.summary = summary
        row.error_message = (error_message or None) and error_message[:500]
        row.finished_at = now
        self._session.flush()
        return row

    def get_trace(self, trace_id: UUID) -> ProcessTraceRow | None:
        """Load one trace header."""
        return self._session.get(ProcessTraceRow, trace_id)

    def list_steps(self, trace_id: UUID) -> list[ProcessTraceStepRow]:
        """Ordered steps for a trace."""
        return list(
            self._session.scalars(
                select(ProcessTraceStepRow)
                .where(ProcessTraceStepRow.trace_id == trace_id)
                .order_by(ProcessTraceStepRow.position)
            ).all()
        )

    def list_by_correlation(self, correlation_id: str) -> list[ProcessTraceRow]:
        """All traces sharing a correlation id (oldest first)."""
        return list(
            self._session.scalars(
                select(ProcessTraceRow)
                .where(ProcessTraceRow.correlation_id == correlation_id)
                .order_by(ProcessTraceRow.created_at)
            ).all()
        )

    def list_traces(
        self,
        *,
        page: int,
        page_size: int,
        context: str | None = None,
        operation: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        correlation_id: str | None = None,
        status: str | None = None,
    ) -> tuple[list[ProcessTraceRow], int]:
        """Filter and page process traces."""
        stmt: Select[tuple[ProcessTraceRow]] = select(ProcessTraceRow)
        count_stmt = select(func.count()).select_from(ProcessTraceRow)
        if context:
            stmt = stmt.where(ProcessTraceRow.context == context)
            count_stmt = count_stmt.where(ProcessTraceRow.context == context)
        if operation:
            stmt = stmt.where(ProcessTraceRow.operation == operation)
            count_stmt = count_stmt.where(ProcessTraceRow.operation == operation)
        if entity_type:
            stmt = stmt.where(ProcessTraceRow.entity_type == entity_type)
            count_stmt = count_stmt.where(ProcessTraceRow.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(ProcessTraceRow.entity_id == entity_id)
            count_stmt = count_stmt.where(ProcessTraceRow.entity_id == entity_id)
        if correlation_id:
            stmt = stmt.where(ProcessTraceRow.correlation_id == correlation_id)
            count_stmt = count_stmt.where(ProcessTraceRow.correlation_id == correlation_id)
        if status:
            stmt = stmt.where(ProcessTraceRow.status == status)
            count_stmt = count_stmt.where(ProcessTraceRow.status == status)
        total = int(self._session.scalar(count_stmt) or 0)
        rows = self._session.scalars(
            stmt.order_by(ProcessTraceRow.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total
