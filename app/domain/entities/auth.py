"""Authentication-related domain entities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserCredential:
    """Stored credential for a user account."""

    user_id: str
    username: str
    password_hash: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.user_id or not self.username or not self.password_hash:
            raise ValueError("user_id, username, and password_hash are required")
