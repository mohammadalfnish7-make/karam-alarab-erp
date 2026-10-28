from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from database.repositories.trace_repository import SqlAlchemyTraceRepository
from support.logging import request_id_var

logger = logging.getLogger(__name__)


class TraceRecorder:
    """Core process-trace writer for every bounded context (short DB sessions)."""

    def __init__(self, session_factory: sessionmaker) -> None:
        """Keep a session factory so traces survive failed business UoWs."""
        self._session_factory = session_factory

    def start(
        self,
        *,
        context: str,
        operation: str,
        correlation_id: str,
        entity_type: str = "",
        entity_id: str = "",
        summary: str = "",
        request_id: str | None = None,
    ) -> UUID | None:
        """Open a running trace; return its id (None if persistence fails)."""
        now = datetime.now(UTC)
        rid = request_id if request_id is not None else request_id_var.get("-")
        session = self._session_factory()
        try:
            repo = SqlAlchemyTraceRepository(session)
            row = repo.create_trace(
                correlation_id=str(correlation_id),
                request_id=rid or "-",
                context=context,
                operation=operation,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id else "",
                summary=summary or f"Started {operation}.",
                now=now,
            )
            repo.add_step(
                trace_id=row.id,
                step_key="start",
                status="succeeded",
                summary=summary or f"Started {operation}.",
                detail={"context": context, "operation": operation},
                duration_ms=None,
                now=now,
            )
            session.commit()
            logger.info(
                "process_trace_started",
                extra={
                    "trace_id": str(row.id),
                    "correlation_id": str(correlation_id),
                    "context": context,
                    "operation": operation,
                    "request_id": rid,
                },
            )
            return row.id
        except Exception:
            session.rollback()
            logger.exception(
                "process_trace_start_failed",
                extra={
                    "correlation_id": str(correlation_id),
                    "context": context,
                    "operation": operation,
                },
            )
            return None
        finally:
            session.close()

    def step(
        self,
        trace_id: UUID | None,
        *,
        step_key: str,
        status: str,
        summary: str,
        detail: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Append a stage-boundary step (no-op if trace_id is None)."""
        if trace_id is None:
            return
        now = datetime.now(UTC)
        session = self._session_factory()
        try:
            repo = SqlAlchemyTraceRepository(session)
            repo.add_step(
                trace_id=trace_id,
                step_key=step_key,
                status=status,
                summary=summary,
                detail=_safe_detail(detail),
                duration_ms=duration_ms,
                now=now,
            )
            session.commit()
            logger.info(
                "process_trace_step",
                extra={
                    "trace_id": str(trace_id),
                    "step_key": step_key,
                    "status": status,
                },
            )
        except Exception:
            session.rollback()
            logger.exception(
                "process_trace_step_failed",
                extra={"trace_id": str(trace_id), "step_key": step_key},
            )
        finally:
            session.close()

    def succeed(self, trace_id: UUID | None, *, summary: str) -> None:
        """Mark the trace as succeeded."""
        self._finish(trace_id, status="succeeded", summary=summary, error_message=None)

    def fail(self, trace_id: UUID | None, *, summary: str, error_message: str) -> None:
        """Mark the trace as failed with a safe error message."""
        self._finish(
            trace_id,
            status="failed",
            summary=summary,
            error_message=error_message[:500],
        )

    def partial(self, trace_id: UUID | None, *, summary: str, error_message: str | None = None) -> None:
        """Mark the trace as partial (some steps failed)."""
        self._finish(
            trace_id,
            status="partial",
            summary=summary,
            error_message=(error_message or "")[:500] or None,
        )

    def record_handler_failure(
        self,
        *,
        event_type: str,
        event_id: str,
        error_message: str,
        entity_id: str = "",
    ) -> None:
        """Best-effort trace when EventBus swallows a handler exception."""
        trace_id = self.start(
            context="support",
            operation="event_handler",
            correlation_id=event_id,
            entity_type="domain_event",
            entity_id=entity_id or event_type,
            summary=f"Event handler failed for {event_type}.",
        )
        self.step(
            trace_id,
            step_key="handler",
            status="failed",
            summary=f"Handler for {event_type} raised an error.",
            detail={"eventType": event_type, "errorType": error_message.split(":")[0][:64]},
        )
        self.fail(
            trace_id,
            summary=f"Event handler failed for {event_type}.",
            error_message=error_message,
        )

    def _finish(
        self,
        trace_id: UUID | None,
        *,
        status: str,
        summary: str,
        error_message: str | None,
    ) -> None:
        if trace_id is None:
            return
        now = datetime.now(UTC)
        session = self._session_factory()
        try:
            repo = SqlAlchemyTraceRepository(session)
            repo.add_step(
                trace_id=trace_id,
                step_key="finish",
                status=status if status in {"succeeded", "failed", "partial"} else "succeeded",
                summary=summary,
                detail={"finalStatus": status},
                duration_ms=None,
                now=now,
            )
            repo.finish_trace(
                trace_id,
                status=status,
                summary=summary,
                error_message=error_message,
                now=now,
            )
            session.commit()
            logger.info(
                "process_trace_finished",
                extra={
                    "trace_id": str(trace_id),
                    "status": status,
                },
            )
        except Exception:
            session.rollback()
            logger.exception(
                "process_trace_finish_failed",
                extra={"trace_id": str(trace_id), "status": status},
            )
        finally:
            session.close()


def _safe_detail(detail: dict[str, Any] | None) -> dict[str, Any]:
    """Drop obvious secret-like keys from step detail."""
    if not detail:
        return {}
    blocked = {"password", "secret", "token", "authorization", "webhook_secret"}
    out: dict[str, Any] = {}
    for key, value in detail.items():
        if key.lower() in blocked or "secret" in key.lower() or "password" in key.lower():
            continue
        out[key] = value
    return out
