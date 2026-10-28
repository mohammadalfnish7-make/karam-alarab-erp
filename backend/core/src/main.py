from __future__ import annotations

import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# Sibling vertical packages for uvicorn --app-dir src.
_BACKEND = Path(__file__).resolve().parents[2]
for _name in ("work", "notify"):
    _src = _BACKEND / _name / "src"
    if _src.is_dir() and str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import database.models  # noqa: F401 — platform tables
import notify.database.models  # noqa: F401 — notify tables (composition root)
import work.database.models  # noqa: F401 — work_* task tables (composition root)
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
from domain.shared.domain_event import DomainEvent
from notify.api.channel_router import router as channel_router
from notify.api.delivery_router import router as delivery_router
from notify.api.notification_router import router as notification_router
from notify.application.commands import AssignNotifyCommand
from notify.application.notify_listener import NotifyListener
from support.events import EventBus
from support.logging import configure_logging, request_id_var
from support.tracing import TraceRecorder
from work.api.work_router import router as work_router
from work.domain.events import TaskAssigned


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

    for event_type in (
        UserRegistered,
        UserDeactivated,
        UserRolesChanged,
        UserPasswordChanged,
        LoginFailed,
    ):
        event_bus.subscribe(event_type, audit_listener.handle)
    event_bus.subscribe(TaskAssigned, on_task_assigned)

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
        yield
        engine.dispose()

    app = FastAPI(title="Karam Al Arab ERP API", lifespan=lifespan)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.event_bus = event_bus
    app.state.settings = settings
    app.state.upload_dir = upload_dir
    app.state.trace_recorder = trace_recorder
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
