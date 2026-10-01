"""Investment entity - represents a single investment (stock, bond, etc.)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domain.value_objects import (
    Identifier,
    InvestmentType,
    InvestmentTypeValidator,
    Money,
)


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
    held_to_maturity: bool = False  # Bonds held until redemption
    face_value: Optional[Money] = None  # Per-unit nominal value (for bonds)
    name: Optional[str] = None  # Human-readable security name (bank title or OpenFIGI)

    def __post_init__(self):
        """Validate investment data after initialization."""
        if not self.id or not self.portfolio_id:
            raise ValueError("id and portfolio_id are required")
        if not isinstance(self.identifier, Identifier):
            raise ValueError("identifier must be an Identifier value object")
        if not isinstance(self.type, InvestmentType):
            raise ValueError("type must be an InvestmentType")
        if not isinstance(self.held_to_maturity, bool):
            raise ValueError("held_to_maturity must be a bool")
        if self.face_value is not None and not isinstance(
            self.face_value, Money
        ):
            raise ValueError("face_value must be a Money value object")
        if self.name is not None:
            if not isinstance(self.name, str):
                raise ValueError("name must be a string or None")
            object.__setattr__(self, "name", self.name.strip()[:200] or None)

    def update_details(
        self,
        type: Optional[InvestmentType] = None,
        held_to_maturity: Optional[bool] = None,
        face_value: Optional[Money] = None,
        name: Optional[str] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        """Update investment metadata (limited fields to preserve identifier)."""
        if type is not None:
            if not isinstance(type, InvestmentType):
                raise ValueError("type must be an InvestmentType")
            object.__setattr__(self, "type", type)

        if held_to_maturity is not None:
            if not isinstance(held_to_maturity, bool):
                raise ValueError("held_to_maturity must be a bool")
            object.__setattr__(self, "held_to_maturity", held_to_maturity)

        if face_value is not None:
            if not isinstance(face_value, Money):
                raise ValueError("face_value must be a Money value object")
            object.__setattr__(self, "face_value", face_value)

        if name is not None:
            if not isinstance(name, str):
                raise ValueError("name must be a string")
            object.__setattr__(self, "name", name.strip()[:200] or None)

        object.__setattr__(
            self, "updated_at", updated_at or datetime.utcnow()
        )
