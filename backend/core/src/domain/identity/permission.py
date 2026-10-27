from __future__ import annotations

import re

from domain.shared.domain_error import ValidationError

_PERMISSION_NAME = re.compile(r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$")


def normalize_permission_name(name: str) -> str:
    """Validate and normalize a permission as lowercase `resource:action`."""
    value = name.strip().lower()
    if not _PERMISSION_NAME.match(value):
        raise ValidationError(
            "Permission must look like resource:action (lowercase).",
            fields={"name": "Permission must look like resource:action (lowercase)."},
        )
    return value
