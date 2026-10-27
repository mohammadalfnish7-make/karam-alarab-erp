from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN = frozenset({"fastapi", "pydantic", "sqlalchemy", "starlette", "uvicorn"})


def test_domain_packages_have_no_framework_imports() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "domain"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".", 1)[0]
                    if top in FORBIDDEN:
                        offenders.append(f"{path}:{alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".", 1)[0]
                if top in FORBIDDEN:
                    offenders.append(f"{path}:{node.module}")
    assert offenders == []
