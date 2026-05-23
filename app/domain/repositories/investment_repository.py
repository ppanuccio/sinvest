"""Abstract investment repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, List

from app.domain.entities.investment import Investment


class InvestmentRepository(ABC):
    """Abstract repository for Investment persistence."""

    @abstractmethod
    def save(self, investment: Investment) -> Investment:
        """Save a new investment."""
        pass

    @abstractmethod
    def get_by_id(self, investment_id: str) -> Optional[Investment]:
        """Get an investment by ID."""
        pass

    @abstractmethod
    def list_by_portfolio(self, portfolio_id: str) -> List[Investment]:
        """Get all investments in a portfolio."""
        pass

    @abstractmethod
    def update(self, investment: Investment) -> Investment:
        """Update an existing investment."""
        pass

    @abstractmethod
    def delete(self, investment_id: str) -> bool:
        """Delete an investment. Returns True if deleted."""
        pass

    @abstractmethod
    def exists(self, investment_id: str) -> bool:
        """Check if investment exists."""
        pass
