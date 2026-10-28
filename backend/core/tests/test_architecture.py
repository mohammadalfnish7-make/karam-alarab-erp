from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_FRAMEWORK = frozenset({"fastapi", "pydantic", "sqlalchemy", "starlette", "uvicorn"})

CORE_VERTICAL_IMPORT_ALLOWLIST = frozenset({"main.py"})


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _domain_roots() -> list[Path]:
    backend = _backend_root()
    return [
        backend / "core" / "src" / "domain",
        backend / "work" / "src" / "work" / "domain",
        backend / "notify" / "src" / "notify" / "domain",
        backend / "filemanager" / "src" / "filemanager" / "domain",
    ]


def test_domain_packages_have_no_framework_imports() -> None:
    offenders: list[str] = []
    for root in _domain_roots():
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".", 1)[0]
                        if top in FORBIDDEN_FRAMEWORK:
                            offenders.append(f"{path}:{alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    top = node.module.split(".", 1)[0]
                    if top in FORBIDDEN_FRAMEWORK:
                        offenders.append(f"{path}:{node.module}")
    assert offenders == []


def _imports_package(path: Path, package: str) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == package or alias.name.startswith(f"{package}."):
                    return True
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == package or node.module.startswith(f"{package}."):
                return True
    return False


def test_core_does_not_import_verticals_except_composition_root() -> None:
    """Verticals may import core; core must not import verticals except the host."""
    core_src = _backend_root() / "core" / "src"
    offenders: list[str] = []
    for path in core_src.rglob("*.py"):
        rel = path.relative_to(core_src).as_posix()
        if rel in CORE_VERTICAL_IMPORT_ALLOWLIST:
            continue
        if any(
            _imports_package(path, package) for package in ("work", "notify", "filemanager")
        ):
            offenders.append(rel)
    assert offenders == [], f"core imported verticals outside composition root: {offenders}"


def test_work_does_not_import_notify_or_filemanager() -> None:
    work_src = _backend_root() / "work" / "src" / "work"
    offenders = [
        path.relative_to(work_src).as_posix()
        for path in work_src.rglob("*.py")
        if _imports_package(path, "notify") or _imports_package(path, "filemanager")
    ]
    assert offenders == [], f"work imported another vertical: {offenders}"


def test_notify_does_not_import_work_or_filemanager() -> None:
    notify_src = _backend_root() / "notify" / "src" / "notify"
    offenders = [
        path.relative_to(notify_src).as_posix()
        for path in notify_src.rglob("*.py")
        if _imports_package(path, "work") or _imports_package(path, "filemanager")
    ]
    assert offenders == [], f"notify imported another vertical: {offenders}"


def test_filemanager_does_not_import_other_verticals() -> None:
    root = _backend_root() / "filemanager" / "src" / "filemanager"
    offenders = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if _imports_package(path, "work") or _imports_package(path, "notify")
    ]
    assert offenders == [], f"filemanager imported another vertical: {offenders}"


def test_host_alembic_registers_all_context_models() -> None:
    """Migrations are host infrastructure, not inside IdentityAccess."""
    env = _backend_root() / "alembic" / "env.py"
    assert env.is_file(), "expected backend/alembic/env.py (Clean Architecture host)"
    assert not (_backend_root() / "core" / "alembic").exists()
    assert _imports_package(env, "work")
    assert _imports_package(env, "notify")
    assert _imports_package(env, "filemanager")
    text = env.read_text(encoding="utf-8")
    assert "database.models" in text
