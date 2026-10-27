from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class UserId:
    """Opaque staff user identity (UUID), never a sequential number."""

    value: UUID

    @classmethod
    def generate(cls) -> UserId:
        """Create a new random user id."""
        return cls(uuid4())

    @classmethod
    def from_string(cls, raw: str) -> UserId:
        """Parse a UUID string into a UserId."""
        return cls(UUID(raw))

    def __str__(self) -> str:
        """String form used in APIs and logs."""
        return str(self.value)
