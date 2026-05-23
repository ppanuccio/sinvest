"""Data Transfer Objects for Transaction-related operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal


# ============= Request DTOs =============

@dataclass
class CreateTransactionDTO:
    """DTO for creating a new transaction."""

    investment_id: str
    amount: Decimal
    quantity: Decimal
    broker: str
    date: datetime


@dataclass
class UpdateTransactionDTO:
    """DTO for updating transaction details."""

    amount: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    broker: Optional[str] = None
    date: Optional[datetime] = None


@dataclass
class GetTransactionDTO:
    """DTO for retrieving a transaction."""

    transaction_id: str
    user_id: str


@dataclass
class ListTransactionsDTO:
    """DTO for listing transactions for an investment."""

    investment_id: str
    user_id: str


# ============= Response DTOs =============

@dataclass
class TransactionResponseDTO:
    """DTO returned for transaction operations."""

    id: str
    investment_id: str
    amount: Decimal
    quantity: Decimal
    broker: str
    date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
