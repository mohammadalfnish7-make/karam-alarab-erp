"""File catalog tests share the app factory fixtures (pythonpath includes core)."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["ENVIRONMENT"] = "test"
os.environ["SEED_ADMIN_EMAIL"] = "admin@karam-alarab.com"
os.environ["SEED_ADMIN_PASSWORD"] = "test-admin-password-123"
os.environ["SEED_OPS_EMAIL"] = "ops@karam-alarab.com"
os.environ["SEED_OPS_PASSWORD"] = "test-ops-password-123"
os.environ["WEB_ORIGIN"] = "http://testserver"

from config.settings import Settings, get_settings
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD
from main import create_app


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture()
def settings(db_path: Path, tmp_path: Path) -> Settings:
    get_settings.cache_clear()
    return Settings(
        environment="test",
        database_url=f"sqlite:///{db_path}",
        seed_admin_email=ADMIN_EMAIL,
        seed_admin_password=ADMIN_PASSWORD,
        seed_ops_email="ops@karam-alarab.com",
        seed_ops_password="test-ops-password-123",
        web_origin="http://testserver",
        session_cookie_name="karam_session",
        session_ttl_seconds=28800,
        upload_dir=str(tmp_path / "uploads"),
    )


@pytest.fixture()
def client(settings: Settings) -> Generator[TestClient]:
    get_settings.cache_clear()
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


@pytest.fixture()
def admin_client(client: TestClient) -> TestClient:
    response = client.post(
        "/sessions",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return client
