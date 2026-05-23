"""Abstract price history repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from app.domain.entities.price_history import PriceHistory


class PriceHistoryRepository(ABC):
    """Abstract repository for PriceHistory persistence."""

    @abstractmethod
    def save(self, price_history: PriceHistory) -> PriceHistory:
        """Save a new price history record."""
        pass

    @abstractmethod
    def get_by_id(self, price_history_id: str) -> Optional[PriceHistory]:
        """Get a price history record by ID."""
        pass

    @abstractmethod
    def get_latest_price(self, investment_id: str) -> Optional[PriceHistory]:
        """Get the most recent price for an investment."""
        pass

    @abstractmethod
    def list_by_investment(self, investment_id: str) -> List[PriceHistory]:
        """Get all price records for an investment, ordered by date descending."""
        pass

    @abstractmethod
    def list_by_investment_and_date_range(
        self,
        investment_id: str,
        from_date: datetime,
        to_date: datetime,
    ) -> List[PriceHistory]:
        """Get price records within a date range, ordered by date descending."""
        pass

    @abstractmethod
    def delete(self, price_history_id: str) -> bool:
        """Delete a price record. Returns True if deleted."""
        pass

    @abstractmethod
    def delete_by_investment(self, investment_id: str) -> int:
        """Delete all price records for an investment. Returns count deleted."""
        pass
