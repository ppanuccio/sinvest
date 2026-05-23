"""Transaction entity - represents a buy/sell transaction."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.domain.value_objects import Money, Quantity


@dataclass
class Transaction:
    """
    Transaction entity - represents a single buy/sell transaction.
    Amount is the total cost, quantity is the number of units.
    """

    id: str
    investment_id: str
    amount: Money  # Total cost of this transaction
    quantity: Quantity  # Number of units acquired
    broker: str
    date: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate transaction data after initialization."""
        if not self.id or not self.investment_id:
            raise ValueError("id and investment_id are required")
        if not isinstance(self.amount, Money):
            raise ValueError("amount must be a Money value object")
        if not isinstance(self.quantity, Quantity):
            raise ValueError("quantity must be a Quantity value object")
        if not self.broker or len(self.broker) < 1:
            raise ValueError("broker name is required")
        if self.date > datetime.utcnow():
            raise ValueError("transaction date cannot be in the future")

    @property
    def price_per_unit(self) -> Decimal:
        """Calculate the price per unit for this transaction."""
        return self.amount.amount / self.quantity.value

    def update_details(
        self,
        amount: Money | None = None,
        quantity: Quantity | None = None,
        broker: str | None = None,
        date: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        """Update transaction details."""
        if amount is not None:
            if not isinstance(amount, Money):
                raise ValueError("amount must be a Money value object")
            object.__setattr__(self, "amount", amount)

        if quantity is not None:
            if not isinstance(quantity, Quantity):
                raise ValueError("quantity must be a Quantity value object")
            object.__setattr__(self, "quantity", quantity)

        if broker is not None:
            if not broker or len(broker) < 1:
                raise ValueError("broker name is required")
            object.__setattr__(self, "broker", broker)

        if date is not None:
            if date > datetime.utcnow():
                raise ValueError("transaction date cannot be in the future")
            object.__setattr__(self, "date", date)

        object.__setattr__(
            self, "updated_at", updated_at or datetime.utcnow()
        )
