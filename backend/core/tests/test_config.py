from __future__ import annotations

import pytest

from config.settings import Settings


def test_production_rejects_sqlite() -> None:
    settings = Settings(
        environment="production",
        database_url="sqlite:///./var/karam.db",
        seed_admin_password="unused-in-production-check",
    )
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        settings.validate_runtime()
