"""Application security abstractions."""

from abc import ABC, abstractmethod
from typing import Optional


class PasswordHasher(ABC):
    """Hash and verify user passwords."""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Return a storable password hash."""
        pass

    @abstractmethod
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Return True when password matches the stored hash."""
        pass


class TokenService(ABC):
    """Issue and verify authentication tokens."""

    @abstractmethod
    def issue_token(self, user_id: str) -> str:
        """Create an access token for a user."""
        pass

    @abstractmethod
    def verify_token(self, token: str) -> Optional[str]:
        """Return the authenticated user ID, or None if invalid."""
        pass
