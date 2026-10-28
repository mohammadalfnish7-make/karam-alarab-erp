"""Host migration environment — infrastructure detail (Clean Architecture outer ring).

Registers every vertical's SQLAlchemy models onto the shared Base. Not part of
IdentityAccess; lives beside core/work/notify/filemanager so schema history is one deploy story.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

_BACKEND = Path(__file__).resolve().parents[1]
for _p in (
    _BACKEND / "core" / "src",
    _BACKEND / "work" / "src",
    _BACKEND / "notify" / "src",
    _BACKEND / "filemanager" / "src",
):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from config.settings import get_settings
from database.engine import Base

import database.models  # noqa: F401
import filemanager.database.models  # noqa: F401
import notify.database.models  # noqa: F401
import work.database.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection."""
    url = get_settings().database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the configured database URL."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_settings().database_url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
