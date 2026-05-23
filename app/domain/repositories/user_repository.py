"""Abstract repository interfaces - define contracts for data persistence."""

from abc import ABC, abstractmethod
from typing import Optional, List

from app.domain.entities.user import User


class UserRepository(ABC):
    """Abstract repository for User persistence."""

    @abstractmethod
    def save(self, user: User) -> User:
        """Save a new user. Returns the saved user."""
        pass

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID. Returns None if not found."""
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username. Returns None if not found."""
        pass

    @abstractmethod
    def exists_by_username(self, username: str) -> bool:
        """Check if a user with given username exists."""
        pass

    @abstractmethod
    def list_all(self) -> List[User]:
        """Get all users."""
        pass

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Delete a user. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    def update(self, user: User) -> User:
        """Update an existing user."""
        pass
