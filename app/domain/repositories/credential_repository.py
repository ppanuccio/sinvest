"""Credential repository interface."""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.auth import UserCredential


class CredentialRepository(ABC):
    """Abstract repository for user credentials."""

    @abstractmethod
    def save(self, credential: UserCredential) -> UserCredential:
        """Save user credentials."""
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[UserCredential]:
        """Get credentials by username."""
        pass

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> Optional[UserCredential]:
        """Get credentials by user ID."""
        pass

    @abstractmethod
    def delete_by_user_id(self, user_id: str) -> bool:
        """Delete credentials by user ID."""
        pass
