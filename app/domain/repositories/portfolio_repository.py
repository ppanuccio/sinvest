"""Abstract portfolio repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, List

from app.domain.entities.portfolio import Portfolio


class PortfolioRepository(ABC):
    """Abstract repository for Portfolio persistence."""

    @abstractmethod
    def save(self, portfolio: Portfolio) -> Portfolio:
        """Save a new portfolio."""
        pass

    @abstractmethod
    def get_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        """Get a portfolio by ID."""
        pass

    @abstractmethod
    def list_by_user(self, user_id: str) -> List[Portfolio]:
        """Get all portfolios for a user."""
        pass

    @abstractmethod
    def update(self, portfolio: Portfolio) -> Portfolio:
        """Update an existing portfolio."""
        pass

    @abstractmethod
    def delete(self, portfolio_id: str) -> bool:
        """Delete a portfolio. Returns True if deleted."""
        pass

    @abstractmethod
    def exists(self, portfolio_id: str) -> bool:
        """Check if portfolio exists."""
        pass
