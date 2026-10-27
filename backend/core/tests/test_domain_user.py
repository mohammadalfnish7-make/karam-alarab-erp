from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.identity.user import User
from domain.shared.domain_error import ConflictError, ValidationError


def test_last_admin_cannot_be_deactivated() -> None:
    now = datetime.now(UTC)
    user = User.register(
        email="admin@example.com",
        password_hash="hash",
        role_names={"admin"},
        now=now,
    )
    with pytest.raises(ConflictError):
        user.deactivate(now=now, remaining_admins=1)


def test_invalid_email_rejected() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        User.register(
            email="not-an-email",
            password_hash="hash",
            role_names={"sales"},
            now=now,
        )
