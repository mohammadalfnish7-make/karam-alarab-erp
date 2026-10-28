from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

from domain.shared.domain_event import DomainEvent

if TYPE_CHECKING:
    from support.tracing import TraceRecorder

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=DomainEvent)
EventHandler = Callable[[DomainEvent], None]


class EventBus:
    """In-process publish/subscribe. Handler failures are logged, not re-raised."""

    def __init__(self, trace_recorder: TraceRecorder | None = None) -> None:
        """Start with an empty handler map; optional TraceRecorder for failures."""
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}
        self._trace_recorder = trace_recorder

    def set_trace_recorder(self, trace_recorder: TraceRecorder) -> None:
        """Attach a TraceRecorder after construction (avoids circular wiring)."""
        self._trace_recorder = trace_recorder

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        """Register a handler for one event type."""
        self._handlers.setdefault(event_type, []).append(handler)  # type: ignore[arg-type]

    def publish(self, event: DomainEvent) -> None:
        """Notify all handlers for this event type."""
        for handler in self._handlers.get(type(event), []):
            try:
                handler(event)
            except Exception as exc:
                logger.exception(
                    "event_handler_failed",
                    extra={
                        "event_type": type(event).__name__,
                        "event_id": str(event.event_id),
                        "correlation_id": str(event.event_id),
                    },
                )
                if self._trace_recorder is not None:
                    try:
                        self._trace_recorder.record_handler_failure(
                            event_type=type(event).__name__,
                            event_id=str(event.event_id),
                            error_message=f"{type(exc).__name__}: {exc}",
                            entity_id=getattr(event, "aggregate_id", "") or "",
                        )
                    except Exception:
                        logger.exception("event_handler_trace_failed")

    def publish_all(self, events: list[DomainEvent]) -> None:
        """Publish a list of events in order."""
        for event in events:
            self.publish(event)


class UnitOfWork:
    """Commit the SQLAlchemy session, then publish collected domain events."""

    def __init__(self, session, event_bus: EventBus) -> None:  # noqa: ANN001
        """Bind a DB session and event bus for one use-case commit."""
        self.session = session
        self.event_bus = event_bus
        self._events: list[DomainEvent] = []

    def collect(self, events: list[DomainEvent]) -> None:
        """Queue domain events to publish after a successful commit."""
        self._events.extend(events)

    def commit(self) -> None:
        """Persist DB changes, then publish queued events."""
        self.session.commit()
        events = list(self._events)
        self._events.clear()
        self.event_bus.publish_all(events)

    def rollback(self) -> None:
        """Undo the DB transaction and drop queued events."""
        self.session.rollback()
        self._events.clear()
