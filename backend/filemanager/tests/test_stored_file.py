from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from domain.shared.domain_error import NotFoundError, ValidationError
from domain.shared.user_id import UserId
from filemanager.api.disposition import content_disposition
from filemanager.application.file_service import FileService
from filemanager.domain.stored_file import MAX_FILE_BYTES, StoredFile
from filemanager.storage.local_blob_store import LocalBlobStore
from support.events import UnitOfWork


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 10, 28, tzinfo=UTC)


def _register(**overrides: object) -> StoredFile:
    payload: dict[str, object] = {
        "display_name": "note.txt",
        "content_type": "text/plain",
        "data": b"hello",
        "sha256": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        "uploaded_by": UserId.generate(),
        "actor_email": "admin@karam-alarab.com",
        "now": datetime(2026, 10, 28, tzinfo=UTC),
    }
    payload.update(overrides)
    return StoredFile.register(**payload)  # type: ignore[arg-type]


def test_register_strips_path_and_keeps_final_name() -> None:
    stored = _register(display_name="../../secret.txt")
    assert stored.display_name == "secret.txt"
    assert stored.status == "available"
    assert stored.storage_key != stored.display_name
    assert len(stored.pull_events()) == 1


def test_register_rejects_empty_oversize_and_mismatched_type() -> None:
    with pytest.raises(ValidationError, match="Filename is required"):
        _register(display_name="   ")
    with pytest.raises(ValidationError, match="Empty files"):
        _register(data=b"")
    with pytest.raises(ValidationError, match="too large"):
        _register(data=b"x" * (MAX_FILE_BYTES + 1))
    with pytest.raises(ValidationError, match="not allowed"):
        _register(content_type="text/html", data=b"<html></html>")
    with pytest.raises(ValidationError, match="do not match"):
        _register(content_type="application/pdf", data=b"not a pdf")


def test_owner_link_requires_both_fields() -> None:
    with pytest.raises(ValidationError, match="both required"):
        _register(owner_context="freight", owner_id="")
    stored = _register(owner_context="freight", owner_id="shp-1")
    assert stored.owner_context == "freight"
    assert stored.owner_id == "shp-1"


def test_content_disposition_keeps_unicode_and_encodes_quotes() -> None:
    header = content_disposition('накладная "a".txt')
    assert header.startswith("attachment;")
    assert "filename*=UTF-8''" in header
    assert "%D0%BD" in header
    assert "%22" in header
    assert "\r" not in header
    assert "\n" not in header


def test_blob_store_rejects_client_paths(tmp_path: Path) -> None:
    store = LocalBlobStore(tmp_path)
    with pytest.raises(NotFoundError):
        store.put("../secret", b"nope")
    stored = _register()
    store.put(stored.storage_key, b"hello")
    assert store.get(stored.storage_key) == b"hello"
    assert (tmp_path / stored.display_name).exists() is False


class _BoomFiles:
    def add(self, stored: StoredFile) -> None:
        raise RuntimeError("db down")


class _FakeUow(UnitOfWork):
    def __init__(self) -> None:
        self.rolled_back = False

    def collect(self, events: list) -> None:  # type: ignore[override]
        self.events = events

    def commit(self) -> None:
        raise AssertionError("commit should not run")

    def rollback(self) -> None:
        self.rolled_back = True


def test_failed_save_removes_the_blob(tmp_path: Path) -> None:
    blobs = LocalBlobStore(tmp_path)
    uow = _FakeUow()
    service = FileService(
        files=_BoomFiles(),  # type: ignore[arg-type]
        blobs=blobs,
        clock=FixedClock(),
        uow=uow,
    )
    with pytest.raises(RuntimeError, match="db down"):
        service.register(
            uploaded_by=UserId.generate(),
            actor_email="admin@karam-alarab.com",
            display_name="note.txt",
            content_type="text/plain",
            data=b"hello",
        )
    assert uow.rolled_back is True
    assert list(tmp_path.iterdir()) == []
