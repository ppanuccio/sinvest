"""Abstract transaction repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, List

from app.domain.entities.transaction import Transaction


class TransactionRepository(ABC):
    """Abstract repository for Transaction persistence."""

    @abstractmethod
    def save(self, transaction: Transaction) -> Transaction:
        """Save a new transaction."""
        pass

    @abstractmethod
    def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Get a transaction by ID."""
        pass

    @abstractmethod
    def list_by_investment(self, investment_id: str) -> List[Transaction]:
        """Get all transactions for an investment, ordered by date."""
        pass

    @abstractmethod
    def update(self, transaction: Transaction) -> Transaction:
        """Update an existing transaction."""
        pass

    @abstractmethod
    def delete(self, transaction_id: str) -> bool:
        """Delete a transaction. Returns True if deleted."""
        pass

    @abstractmethod
    def exists(self, transaction_id: str) -> bool:
        """Check if transaction exists."""
        pass

    @abstractmethod
    def delete_by_investment(self, investment_id: str) -> int:
        """Delete all transactions for an investment. Returns count deleted."""
        pass
