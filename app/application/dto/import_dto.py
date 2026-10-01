"""Data Transfer Objects for statement import operations."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List

from app.application.dto.investment_dto import InvestmentResponseDTO


# ============= Request DTOs =============


@dataclass(frozen=True)
class ImportedTransactionDTO:
    """A single statement row ready to be imported."""

    identifier: str
    title: str
    kind: str  # 'buy' or 'coupon'
    date: datetime
    quantity: Decimal
    amount: Decimal
    currency: str


# ============= Response DTOs =============


@dataclass(frozen=True)
class InvalidIdentifierDTO:
    """A statement row skipped because its identifier failed validation."""

    identifier: str
    title: str
    reason: str


@dataclass
class ImportResultDTO:
    """Summary of a statement import run."""

    created_investments: List[InvestmentResponseDTO] = field(default_factory=list)
    created_transactions: int = 0
    skipped_transactions: int = 0
    invalid_identifiers: List[InvalidIdentifierDTO] = field(default_factory=list)
