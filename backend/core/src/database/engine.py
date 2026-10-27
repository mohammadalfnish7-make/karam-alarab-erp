from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import Settings, get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all core tables."""



def _ensure_sqlite_dir(url: str) -> None:
    """Create the parent folder for a SQLite file URL if needed."""
    if not url.startswith("sqlite:///"):
        return
    path = Path(url.removeprefix("sqlite:///"))
    if path.parent and str(path.parent) not in {".", ""}:
        path.parent.mkdir(parents=True, exist_ok=True)


def create_db_engine(settings: Settings | None = None):
    """Build the SQLAlchemy engine (SQLite demo or Postgres)."""
    settings = settings or get_settings()
    _ensure_sqlite_dir(settings.database_url)
    connect_args: dict = {}
    if settings.is_sqlite:
        connect_args["check_same_thread"] = False
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    if settings.is_sqlite:

        @event.listens_for(engine, "connect")
        def _sqlite_pragma(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
            """Enable SQLite foreign-key enforcement on each connection."""
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine) -> sessionmaker[Session]:
    """Return a session factory bound to the engine."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session(session_factory: sessionmaker[Session]) -> Generator[Session]:
    """Yield one DB session and close it afterward."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
