from __future__ import annotations

import re
from pathlib import Path

from domain.shared.domain_error import NotFoundError

_STORAGE_KEY = re.compile(r"^[0-9a-f]{32}$")


class LocalBlobStore:
    """Write-once blobs in one directory. The key is never a client filename."""

    def __init__(self, root: Path) -> None:
        """Store files under `root`, created on the first put."""
        self._root = root

    def put(self, storage_key: str, data: bytes) -> None:
        """Write bytes under a random key, replacing a partial file on failure."""
        path = self._path(storage_key)
        self._root.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + ".part")
        try:
            partial.write_bytes(data)
            partial.replace(path)
        except Exception:
            partial.unlink(missing_ok=True)
            raise

    def get(self, storage_key: str) -> bytes:
        """Read bytes for a key that is a real file in this directory."""
        path = self._path(storage_key)
        if not path.is_file():
            raise NotFoundError("File content is missing.")
        return path.read_bytes()

    def delete(self, storage_key: str) -> None:
        """Remove a blob when the catalog row was not saved."""
        path = self._path(storage_key)
        if path.is_file():
            path.unlink()

    def _path(self, storage_key: str) -> Path:
        if _STORAGE_KEY.fullmatch(storage_key) is None:
            raise NotFoundError("File not found.")
        root = self._root.resolve()
        path = (root / storage_key).resolve()
        if path.parent != root:
            raise NotFoundError("File not found.")
        return path
