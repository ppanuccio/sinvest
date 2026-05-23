"""PriceHistory entity - tracks investment price over time."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.domain.value_objects import Money


@dataclass
class PriceHistory:
    """
    PriceHistory entity - records the price of an investment at a specific date.
    Allows tracking historical price data and calculating current value.
    """

    id: str
    investment_id: str
    price: Money  # Price per unit at this date
    date: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate price history data after initialization."""
        if not self.id or not self.investment_id:
            raise ValueError("id and investment_id are required")
        if not isinstance(self.price, Money):
            raise ValueError("price must be a Money value object")
        if self.date > datetime.utcnow():
            raise ValueError("price date cannot be in the future")
        if self.price.amount == 0:
            raise ValueError("price must be greater than zero")
