"""Investment entity - represents a single investment (stock, bond, etc.)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domain.value_objects import Identifier, InvestmentType, InvestmentTypeValidator


@dataclass
class Investment:
    """
    Investment entity - represents a single investment (e.g., a stock or bond).
    Contains multiple transactions and price history.
    Identifier can be ISIN or ticker.
    """

    id: str
    portfolio_id: str
    identifier: Identifier  # ISIN or ticker
    type: InvestmentType
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate investment data after initialization."""
        if not self.id or not self.portfolio_id:
            raise ValueError("id and portfolio_id are required")
        if not isinstance(self.identifier, Identifier):
            raise ValueError("identifier must be an Identifier value object")
        if not isinstance(self.type, InvestmentType):
            raise ValueError("type must be an InvestmentType")

    def update_details(
        self,
        type: Optional[InvestmentType] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        """Update investment metadata (limited fields to preserve identifier)."""
        if type is not None:
            if not isinstance(type, InvestmentType):
                raise ValueError("type must be an InvestmentType")
            object.__setattr__(self, "type", type)

        object.__setattr__(
            self, "updated_at", updated_at or datetime.utcnow()
        )
