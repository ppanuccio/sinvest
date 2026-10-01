"""Data Transfer Objects for Investment-related operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal


# ============= Request DTOs =============

@dataclass
class CreateInvestmentDTO:
    """DTO for creating a new investment."""

    portfolio_id: str
    identifier: str
    identifier_type: str  # "ISIN" or "TICKER"
    type: str  # "stock", "bond", "etf", etc.
    held_to_maturity: bool = False
    face_value: Optional[Decimal] = None
    face_value_currency: str = "USD"
    name: Optional[str] = None


@dataclass
class UpdateInvestmentDTO:
    """DTO for updating investment details."""

    type: Optional[str] = None
    held_to_maturity: Optional[bool] = None
    face_value: Optional[Decimal] = None
    face_value_currency: Optional[str] = None
    name: Optional[str] = None


@dataclass
class GetInvestmentDTO:
    """DTO for retrieving an investment."""

    investment_id: str
    user_id: str


@dataclass
class ListInvestmentsDTO:
    """DTO for listing investments in a portfolio."""

    portfolio_id: str
    user_id: str


# ============= Response DTOs =============

@dataclass
class InvestmentResponseDTO:
    """DTO returned for investment operations."""

    id: str
    portfolio_id: str
    identifier: str
    identifier_type: str
    type: str
    created_at: datetime
    updated_at: Optional[datetime]
    held_to_maturity: bool = False
    face_value: Optional[Decimal] = None
    face_value_currency: str = "USD"
    name: Optional[str] = None

    class Config:
        from_attributes = True


@dataclass
class InvestmentDetailResponseDTO:
    """DTO for detailed investment view with calculated metrics."""

    id: str
    portfolio_id: str
    identifier: str
    identifier_type: str
    type: str
    total_quantity: Decimal
    total_invested: Decimal
    current_price: Optional[Decimal]
    total_value: Decimal
    initial_value: Optional[Decimal]
    yield_amount: Decimal
    yield_percentage: Optional[Decimal]
    transaction_count: int
    price_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    name: Optional[str] = None

    class Config:
        from_attributes = True
