"""User entity - represents a portfolio owner."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """
    User entity - represents a person who owns portfolios.
    Immutable after creation.
    """

    id: str
    username: str
    email: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate user data after initialization."""
        if not self.id or not self.username or not self.email:
            raise ValueError("id, username, and email are required")
        if len(self.username) < 3:
            raise ValueError("username must be at least 3 characters")
        if "@" not in self.email:
            raise ValueError("email must be valid")
