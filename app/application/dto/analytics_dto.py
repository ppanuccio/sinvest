"""Data Transfer Objects for Portfolio Analytics."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
from decimal import Decimal


@dataclass
class InvestmentAnalyticsDTO:
    """Analytics for a single investment."""

    investment_id: str
    identifier: str
    type: str
    total_quantity: Decimal
    total_invested: Decimal
    current_price: Optional[Decimal]
    total_value: Decimal
    initial_value: Optional[Decimal]
    yield_amount: Decimal
    yield_percentage: Optional[Decimal]
    allocation_percentage: Decimal


@dataclass
class PortfolioAnalyticsDTO:
    """Complete analytics for a portfolio."""

    portfolio_id: str
    total_value: Decimal
    total_invested: Decimal
    total_yield: Decimal
    total_yield_percentage: Optional[Decimal]
    allocation: Dict[str, Decimal]  # investment_id: percentage
    investments: List[InvestmentAnalyticsDTO]
    calculated_at: datetime

    class Config:
        from_attributes = True
