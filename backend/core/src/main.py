from __future__ import annotations

import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# Sibling vertical packages for uvicorn --app-dir src.
_BACKEND = Path(__file__).resolve().parents[2]
for _name in ("work", "notify", "filemanager"):
    _src = _BACKEND / _name / "src"
    if _src.is_dir() and str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

import database.models  # noqa: F401 — platform tables
import filemanager.database.models  # noqa: F401 — file catalog tables (composition root)
import notify.database.models  # noqa: F401 — notify tables (composition root)
import work.database.models  # noqa: F401 — work_* task tables (composition root)
from api.audit_router import router as audit_router
from api.errors import register_exception_handlers
from api.session_router import router as session_router
from api.trace_router import router as trace_router
from api.user_router import router as user_router
from application.audit_listener import AuditListener
from config.settings import Settings, get_settings
from database.engine import Base, create_db_engine, create_session_factory
from database.seed import seed_identity_access
from domain.identity.events import (
    LoginFailed,
    UserDeactivated,
    UserPasswordChanged,
    UserRegistered,
    UserRolesChanged,
)
from domain.shared.clock import SystemClock
from domain.shared.domain_event import DomainEvent
from domain.shared.file_catalog import FileCatalog
from filemanager.api.file_router import router as file_router
from filemanager.application.file_service import build_file_service
from filemanager.domain.events import FileRegistered
from notify.api.channel_router import router as channel_router
from notify.api.delivery_router import router as delivery_router
from notify.api.notification_router import router as notification_router
from notify.application.commands import AssignNotifyCommand, ReminderNotifyCommand
from notify.application.notify_listener import NotifyListener
from support.events import EventBus, UnitOfWork
from support.logging import configure_logging, request_id_var
from support.tracing import TraceRecorder
from work.api.work_router import router as work_router
from work.domain.events import (
    TaskAssigned,
    TaskAttachmentAdded,
    TaskAttachmentRemoved,
    TaskCommented,
    TaskCreated,
    TaskDueDateChanged,
    TaskEntityLinked,
    TaskEntityUnlinked,
    TaskFollowerAdded,
    TaskPriorityChanged,
    TaskReminderRequested,
    TaskStatusChanged,
    TaskStepChanged,
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach/propagate X-Request-Id and default Cache-Control: no-store."""

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        """Run the request with a request-id context var on the response."""
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            if request.url.path not in {"/health"}:
                response.headers.setdefault("Cache-Control", "no-store")
            return response
        finally:
            request_id_var.reset(token)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app: DB, audit bus, CORS, routers, health."""
    settings = settings or get_settings()
    configure_logging()
    settings.validate_runtime()

    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    event_bus = EventBus()
    trace_recorder = TraceRecorder(session_factory)
    event_bus.set_trace_recorder(trace_recorder)
    audit_listener = AuditListener(session_factory)
    notify_listener = NotifyListener(session_factory, settings, trace_recorder)

    def on_task_assigned(event: DomainEvent) -> None:
        """Adapt Work TaskAssigned → notify AssignNotifyCommand (no cross-imports)."""
        if not isinstance(event, TaskAssigned):
            return
        notify_listener.handle_assign(
            AssignNotifyCommand(
                event_id=event.event_id,
                occurred_at=event.occurred_at,
                task_id=event.task_id,
                title=event.title,
                task_type_id=event.task_type_id,
                status_key=event.status_key,
                assignee_user_id=event.assignee_user_id,
                assignee_email=event.assignee_email,
                assigner_user_id=event.assigner_user_id,
            )
        )

    def on_task_reminder(event: DomainEvent) -> None:
        """Adapt TaskReminderRequested → notify ReminderNotifyCommand."""
        if not isinstance(event, TaskReminderRequested):
            return
        notify_listener.handle_reminder(
            ReminderNotifyCommand(
                event_id=event.event_id,
                occurred_at=event.occurred_at,
                task_id=event.task_id,
                title=event.title,
                task_type_id=event.task_type_id,
                status_key=event.status_key,
                assignee_user_id=event.assignee_user_id,
                assignee_email=event.assignee_email,
                follower_user_id=event.follower_user_id,
                follower_email=event.follower_email,
                message=event.message,
            )
        )

    for event_type in (
        UserRegistered,
        UserDeactivated,
        UserRolesChanged,
        UserPasswordChanged,
        LoginFailed,
    ):
        event_bus.subscribe(event_type, audit_listener.handle)
    event_bus.subscribe(TaskAssigned, on_task_assigned)
    event_bus.subscribe(TaskReminderRequested, on_task_reminder)

    def on_file_registered(event: DomainEvent) -> None:
        """Adapt FileRegistered → audit row (filemanager does not write audit itself)."""
        if not isinstance(event, FileRegistered):
            return
        audit_listener.record(
            occurred_at=event.occurred_at,
            actor=event.actor_email,
            action="FileRegistered",
            entity="stored_file",
            entity_id=event.aggregate_id,
            summary=event.summary,
        )

    event_bus.subscribe(FileRegistered, on_file_registered)

    def on_task_created(event: DomainEvent) -> None:
        """Adapt TaskCreated → audit row."""
        if not isinstance(event, TaskCreated):
            return
        due = f", due {event.due_on}" if event.due_on else ""
        audit_listener.record(
            occurred_at=event.occurred_at,
            actor=event.actor_email or "system",
            action="TaskCreated",
            entity="task",
            entity_id=event.task_id,
            summary=f"Created “{event.title}” ({event.priority}){due}",
        )

    def on_task_assigned_audit(event: DomainEvent) -> None:
        """Adapt TaskAssigned → audit row (notify stays on the other handler)."""
        if not isinstance(event, TaskAssigned):
            return
        audit_listener.record(
            occurred_at=event.occurred_at,
            actor=event.assigner_email or "system",
            action="TaskAssigned",
            entity="task",
            entity_id=event.task_id,
            summary=f"Assigned to {event.assignee_email}",
        )

    def on_task_status_changed(event: DomainEvent) -> None:
        """Adapt TaskStatusChanged → audit row."""
        if not isinstance(event, TaskStatusChanged):
            return
        audit_listener.record(
            occurred_at=event.occurred_at,
            actor=event.actor_email or "system",
            action="TaskStatusChanged",
            entity="task",
            entity_id=event.task_id,
            summary=f"Status {event.from_status_key} → {event.to_status_key}",
        )

    def on_task_due_changed(event: DomainEvent) -> None:
        """Adapt TaskDueDateChanged → audit row."""
        if not isinstance(event, TaskDueDateChanged):
            return
        summary = (
            f"Due date set to {event.due_on}" if event.due_on else "Due date cleared"
        )
        audit_listener.record(
            occurred_at=event.occurred_at,
            actor=event.actor_email or "system",
            action="TaskDueDateChanged",
            entity="task",
            entity_id=event.task_id,
            summary=summary,
        )

    def on_task_priority_changed(event: DomainEvent) -> None:
        """Adapt TaskPriorityChanged → audit row."""
        if not isinstance(event, TaskPriorityChanged):
            return
        audit_listener.record(
            occurred_at=event.occurred_at,
            actor=event.actor_email or "system",
            action="TaskPriorityChanged",
            entity="task",
            entity_id=event.task_id,
            summary=f"Priority set to {event.priority}",
        )

    def on_task_activity(event: DomainEvent) -> None:
        """Adapt step/comment/attachment/link/follower/reminder events → audit rows."""
        if isinstance(event, TaskStepChanged):
            action, summary, actor = "TaskStepChanged", event.summary, event.actor_email
            entity_id = event.task_id
        elif isinstance(event, TaskCommented):
            action, summary, actor = "TaskCommented", event.summary, event.actor_email
            entity_id = event.task_id
        elif isinstance(event, TaskAttachmentAdded):
            action, summary, actor = (
                "TaskAttachmentAdded",
                event.summary,
                event.actor_email,
            )
            entity_id = event.task_id
        elif isinstance(event, TaskAttachmentRemoved):
            action, summary, actor = (
                "TaskAttachmentRemoved",
                event.summary,
                event.actor_email,
            )
            entity_id = event.task_id
        elif isinstance(event, TaskEntityLinked):
            action, summary, actor = "TaskEntityLinked", event.summary, event.actor_email
            entity_id = event.task_id
        elif isinstance(event, TaskEntityUnlinked):
            action, summary, actor = (
                "TaskEntityUnlinked",
                event.summary,
                event.actor_email,
            )
            entity_id = event.task_id
        elif isinstance(event, TaskFollowerAdded):
            action = "TaskFollowerAdded"
            summary = f"Added follower {event.follower_user_id}"
            actor = event.actor_email
            entity_id = event.task_id
        elif isinstance(event, TaskReminderRequested):
            action = "TaskReminderRequested"
            summary = f"Reminder from {event.follower_email}: {event.message}"
            actor = event.follower_email
            entity_id = event.task_id
        else:
            return
        audit_listener.record(
            occurred_at=event.occurred_at,
            actor=actor or "system",
            action=action,
            entity="task",
            entity_id=entity_id,
            summary=summary,
        )

    event_bus.subscribe(TaskCreated, on_task_created)
    event_bus.subscribe(TaskAssigned, on_task_assigned_audit)
    event_bus.subscribe(TaskStatusChanged, on_task_status_changed)
    event_bus.subscribe(TaskDueDateChanged, on_task_due_changed)
    event_bus.subscribe(TaskPriorityChanged, on_task_priority_changed)
    for event_type in (
        TaskStepChanged,
        TaskCommented,
        TaskAttachmentAdded,
        TaskAttachmentRemoved,
        TaskEntityLinked,
        TaskEntityUnlinked,
        TaskFollowerAdded,
        TaskReminderRequested,
    ):
        event_bus.subscribe(event_type, on_task_activity)

    def file_catalog_factory(
        *,
        session: Session,
        uow: UnitOfWork,
        upload_dir: Path,
    ) -> FileCatalog:
        """Request-scoped FileCatalog. Callers depend on the port, not this class."""
        return build_file_service(
            session=session,
            uow=uow,
            upload_dir=upload_dir,
            clock=SystemClock(),
        )

    upload_dir = Path(settings.upload_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Create tables, seed identity, store app state; dispose engine on shutdown."""
        Base.metadata.create_all(bind=engine)
        upload_dir.mkdir(parents=True, exist_ok=True)
        session = session_factory()
        try:
            seed_identity_access(session, settings)
        finally:
            session.close()
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.event_bus = event_bus
        app.state.settings = settings
        app.state.upload_dir = upload_dir
        app.state.trace_recorder = trace_recorder
        app.state.file_catalog_factory = file_catalog_factory
        yield
        engine.dispose()

    app = FastAPI(title="Karam Al Arab ERP API", lifespan=lifespan)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.event_bus = event_bus
    app.state.settings = settings
    app.state.upload_dir = upload_dir
    app.state.trace_recorder = trace_recorder
    app.state.file_catalog_factory = file_catalog_factory
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(session_router)
    app.include_router(user_router)
    app.include_router(work_router)
    app.include_router(channel_router)
    app.include_router(notification_router)
    app.include_router(delivery_router)
    app.include_router(trace_router)
    app.include_router(audit_router)
    app.include_router(file_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness probe used by deploy and local checks."""
        return {"status": "ok"}

    return app


def build_app() -> FastAPI:
    """Entry for uvicorn: `uvicorn main:build_app --factory`."""
    return create_app()


app = None


def __getattr__(name: str):
    """Lazy module-level `app` for `uvicorn main:app`."""
    global app
    if name == "app":
        if app is None:
            app = create_app()
        return app
    raise AttributeError(name)
