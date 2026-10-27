from __future__ import annotations

from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class Argon2PasswordHasher:
    """Hash and verify passwords with Argon2."""

    def __init__(self) -> None:
        """Create the underlying Argon2 hasher."""
        self._hasher = Argon2Hasher()

    def hash(self, password: str) -> str:
        """Create a new Argon2 hash for storage."""
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        """True if the plaintext matches the stored hash."""
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
