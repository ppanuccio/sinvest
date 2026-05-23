"""Portfolio entity - represents a collection of investments."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Portfolio:
    """
    Portfolio entity - a named collection of investments owned by a user.
    Contains multiple investments.
    """

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate portfolio data after initialization."""
        if not self.id or not self.user_id or not self.name:
            raise ValueError("id, user_id, and name are required")
        if len(self.name) < 2:
            raise ValueError("name must be at least 2 characters")

    def update_details(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        """Update portfolio metadata."""
        if name is not None:
            if len(name) < 2:
                raise ValueError("name must be at least 2 characters")
            object.__setattr__(self, "name", name)

        if description is not None:
            object.__setattr__(self, "description", description)

        object.__setattr__(
            self, "updated_at", updated_at or datetime.utcnow()
        )
