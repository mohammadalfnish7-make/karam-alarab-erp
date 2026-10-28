from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from config.settings import Settings
from database.engine import create_db_engine, create_session_factory
from database.models.audit import AuditEntryRow
from helpers import login_as

PDF = b"%PDF-1.4\nhello"
PNG = b"\x89PNG\r\n\x1a\nrest"


def _upload(
    client: TestClient,
    filename: str,
    data: bytes,
    content_type: str,
    **form: str,
) -> dict:
    response = client.post(
        "/files",
        files={"file": (filename, data, content_type)},
        data=form,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_user(admin_client: TestClient, email: str, role: str) -> None:
    response = admin_client.post(
        "/users",
        json={"email": email, "password": "role-password-123", "roles": [role]},
    )
    assert response.status_code == 201, response.text


def test_search_finds_file_by_partial_name(
    admin_client: TestClient,
    settings: Settings,
) -> None:
    created = _upload(admin_client, "Invoice-12.pdf", PDF, "application/pdf")
    assert created["displayName"] == "Invoice-12.pdf"
    assert created["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert "storageKey" not in created
    assert "storage_key" not in created

    found = admin_client.get("/files", params={"name": "invoice"})
    assert found.status_code == 200, found.text
    body = found.json()
    assert body["total"] == 1
    assert body["data"][0]["id"] == created["id"]

    missing = admin_client.get("/files", params={"name": "not-in-catalog"})
    assert missing.status_code == 200
    assert missing.json()["data"] == []
    assert missing.json()["total"] == 0

    catalog = Path(settings.upload_dir) / "catalog"
    names = [path.name for path in catalog.iterdir()]
    assert names == [names[0]]
    assert names[0] != "Invoice-12.pdf"
    assert len(names[0]) == 32

    engine = create_db_engine(settings)
    session = create_session_factory(engine)()
    try:
        rows = session.scalars(
            select(AuditEntryRow).where(AuditEntryRow.action == "FileRegistered")
        ).all()
        assert any(created["id"] == row.entity_id for row in rows)
        assert any("Invoice-12.pdf" in row.summary for row in rows)
    finally:
        session.close()
        engine.dispose()


def test_search_is_case_insensitive_for_cyrillic(admin_client: TestClient) -> None:
    _upload(admin_client, "Накладная.txt", "груз".encode(), "text/plain")
    found = admin_client.get("/files", params={"name": "наклад"})
    assert found.status_code == 200, found.text
    assert found.json()["total"] == 1
    assert found.json()["data"][0]["displayName"] == "Накладная.txt"


def test_like_wildcards_are_literal(admin_client: TestClient) -> None:
    _upload(admin_client, "100%_done.txt", b"ok", "text/plain")
    exact = admin_client.get("/files", params={"name": "100%_"})
    assert exact.status_code == 200, exact.text
    assert exact.json()["total"] == 1
    broad = admin_client.get("/files", params={"name": "100X"})
    assert broad.json()["total"] == 0


def test_path_in_filename_is_not_stored(admin_client: TestClient) -> None:
    created = _upload(admin_client, "../../note.txt", b"hello", "text/plain")
    assert created["displayName"] == "note.txt"
    download = admin_client.get(f"/files/{created['id']}/content")
    assert download.status_code == 200
    assert download.content == b"hello"
    disposition = download.headers["content-disposition"]
    assert "note.txt" in disposition
    assert "../" not in disposition
    assert download.headers["x-content-type-options"] == "nosniff"


def test_unknown_id_is_404(admin_client: TestClient) -> None:
    missing = uuid4()
    assert admin_client.get(f"/files/{missing}").status_code == 404
    assert admin_client.get(f"/files/{missing}/content").status_code == 404


def test_validation_rejects_bad_files(admin_client: TestClient) -> None:
    empty = admin_client.post(
        "/files",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert empty.status_code == 400
    assert "empty" in empty.json()["error"]["message"].lower()

    html = admin_client.post(
        "/files",
        files={"file": ("page.html", b"<html></html>", "text/html")},
    )
    assert html.status_code == 400
    assert "not allowed" in html.json()["error"]["message"].lower()

    fake_pdf = admin_client.post(
        "/files",
        files={"file": ("bad.pdf", b"not a pdf", "application/pdf")},
    )
    assert fake_pdf.status_code == 400
    assert "do not match" in fake_pdf.json()["error"]["message"].lower()

    blank = admin_client.get("/files", params={"name": " "})
    assert blank.status_code == 400
    assert "name" in blank.json()["error"]["fields"]


def test_sales_cannot_read_or_write_files(admin_client: TestClient) -> None:
    created = _upload(admin_client, "pod.png", PNG, "image/png")
    _create_user(admin_client, "sales@karam-alarab.com", "sales")
    login_as(admin_client, "sales@karam-alarab.com", "role-password-123")
    assert admin_client.get("/files", params={"name": "pod"}).status_code == 403
    assert admin_client.get(f"/files/{created['id']}").status_code == 403
    denied = admin_client.post(
        "/files",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert denied.status_code == 403


def test_support_can_search_but_not_upload(admin_client: TestClient) -> None:
    _upload(admin_client, "pod.png", PNG, "image/png")
    _create_user(admin_client, "support@karam-alarab.com", "support")
    login_as(admin_client, "support@karam-alarab.com", "role-password-123")
    found = admin_client.get("/files", params={"name": "pod"})
    assert found.status_code == 200, found.text
    assert found.json()["total"] == 1
    denied = admin_client.post(
        "/files",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert denied.status_code == 403


def test_operations_can_find_a_file_uploaded_by_admin(admin_client: TestClient) -> None:
    _upload(
        admin_client,
        "cargo.json",
        b'{"sku":"perfume"}',
        "application/json",
        owner_context="freight",
        owner_id="shp-1",
    )
    login_as(admin_client, "ops@karam-alarab.com", "test-ops-password-123")
    found = admin_client.get("/files", params={"name": "cargo"})
    assert found.status_code == 200, found.text
    assert found.json()["data"][0]["ownerContext"] == "freight"
    assert found.json()["data"][0]["ownerId"] == "shp-1"


def test_anonymous_cannot_search(client: TestClient) -> None:
    response = client.get("/files", params={"name": "invoice"})
    assert response.status_code == 401
