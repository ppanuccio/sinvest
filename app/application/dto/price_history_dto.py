"""Data Transfer Objects for Price History operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from decimal import Decimal


# ============= Request DTOs =============

@dataclass
class CreatePriceHistoryDTO:
    """DTO for recording a new price."""

    investment_id: str
    price: Decimal
    date: datetime


@dataclass
class GetLatestPriceDTO:
    """DTO for getting latest price for an investment."""

    investment_id: str
    user_id: str


@dataclass
class GetPricesDTO:
    """DTO for getting all prices for an investment."""

    investment_id: str
    user_id: str


@dataclass
class GetPricesByDateRangeDTO:
    """DTO for getting prices within a date range."""

    investment_id: str
    user_id: str
    from_date: datetime
    to_date: datetime


# ============= Response DTOs =============

@dataclass
class PriceHistoryResponseDTO:
    """DTO returned for price history operations."""

    id: str
    investment_id: str
    price: Decimal
    date: datetime
    created_at: datetime

    class Config:
        from_attributes = True
