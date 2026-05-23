"""
Value objects - immutable objects that represent domain concepts.
These enforce validation and domain rules.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from decimal import Decimal
import re
from datetime import datetime

from app.domain.exceptions import (
    InvalidIdentifierException,
    InvalidInvestmentException,
    InvalidTransactionException,
)


class InvestmentType(str, Enum):
    """Types of investments supported."""

    STOCK = "stock"
    BOND = "bond"
    ETF = "etf"
    CRYPTO = "crypto"
    MUTUAL_FUND = "mutual_fund"
    COMMODITY = "commodity"
    OTHER = "other"


class InvestmentTypeValidator:
    """Validates investment type values."""

    @staticmethod
    def validate(value: str) -> InvestmentType:
        """Validate and convert string to InvestmentType."""
        try:
            return InvestmentType(value.lower())
        except ValueError:
            valid_types = ", ".join([t.value for t in InvestmentType])
            raise InvalidInvestmentException(
                f"Invalid investment type '{value}'. Must be one of: {valid_types}"
            )


@dataclass(frozen=True)
class Identifier:
    """
    Immutable value object representing an investment identifier.
    Can be either an ISIN (13 alphanumeric chars) or a ticker (1-5 alphanumeric chars).
    """

    value: str
    identifier_type: str  # "ISIN" or "TICKER"

    def __post_init__(self):
        if not self.value:
            raise InvalidIdentifierException("", "Identifier cannot be empty")

        value_upper = self.value.upper()

        if self.identifier_type.upper() == "ISIN":
            self._validate_isin(value_upper)
        elif self.identifier_type.upper() == "TICKER":
            self._validate_ticker(value_upper)
        else:
            raise InvalidIdentifierException(
                self.value, f"Invalid identifier type: {self.identifier_type}"
            )

    @staticmethod
    def _validate_isin(identifier: str) -> None:
        """Validate ISIN format: 2 letters, 9 alphanumeric, 1 check digit = 12 total."""
        # ISIN format: 2 country code letters + 9 alphanumeric + 1 check digit
        if len(identifier) != 12:
            raise InvalidIdentifierException(
                identifier,
                f"ISIN must be 12 characters, got {len(identifier)}",
            )
        if not re.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$", identifier):
            raise InvalidIdentifierException(
                identifier,
                "ISIN must match format: 2 letters + 9 alphanumeric + 1 digit",
            )

    @staticmethod
    def _validate_ticker(identifier: str) -> None:
        """Validate ticker format: 1-5 alphanumeric characters."""
        if not (1 <= len(identifier) <= 5):
            raise InvalidIdentifierException(
                identifier,
                f"Ticker must be 1-5 characters, got {len(identifier)}",
            )
        if not re.match(r"^[A-Z0-9]+$", identifier):
            raise InvalidIdentifierException(
                identifier,
                "Ticker must be alphanumeric",
            )

    @staticmethod
    def create_isin(value: str) -> "Identifier":
        """Factory method to create an ISIN identifier."""
        return Identifier(value.upper(), "ISIN")

    @staticmethod
    def create_ticker(value: str) -> "Identifier":
        """Factory method to create a ticker identifier."""
        return Identifier(value.upper(), "TICKER")


@dataclass(frozen=True)
class Money:
    """
    Immutable value object representing money with precision.
    Stores amount as Decimal for exact financial calculations.
    Supports negative values for net profit/loss calculations.
    """

    amount: Decimal
    currency: str = "EUR"

    def __post_init__(self):
        if not self.currency or len(self.currency) != 3:
            raise InvalidTransactionException(
                f"Invalid currency code: {self.currency}"
            )

    @property
    def is_zero(self) -> bool:
        return self.amount == 0

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise InvalidTransactionException(
                f"Cannot add {self.currency} and {other.currency}"
            )
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise InvalidTransactionException(
                f"Cannot subtract {self.currency} and {other.currency}"
            )
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Decimal | float | int) -> "Money":
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __rmul__(self, factor: Decimal | float | int) -> "Money":
        return self.__mul__(factor)

    def __truediv__(self, factor: Decimal | float | int) -> "Money":
        if factor == 0:
            raise InvalidTransactionException("Cannot divide by zero")
        return Money(self.amount / Decimal(str(factor)), self.currency)


@dataclass(frozen=True)
class Quantity:
    """Immutable value object representing quantity of an investment."""

    value: Decimal

    def __post_init__(self):
        if self.value <= 0:
            raise InvalidTransactionException(
                "Quantity must be positive"
            )

    @property
    def as_float(self) -> float:
        return float(self.value)

    def __add__(self, other: "Quantity") -> "Quantity":
        return Quantity(self.value + other.value)

    def __sub__(self, other: "Quantity") -> "Quantity":
        result = self.value - other.value
        if result <= 0:
            raise InvalidTransactionException(
                "Quantity cannot be zero or negative"
            )
        return Quantity(result)

    def __mul__(self, factor: Decimal | float | int) -> "Quantity":
        return Quantity(self.value * Decimal(str(factor)))


@dataclass(frozen=True)
class Yield:
    """Immutable value object representing yield (profit/loss)."""

    amount: Decimal  # Can be positive or negative
    percentage: Optional[Decimal] = None  # Optional percentage representation

    def __post_init__(self):
        if self.percentage is not None:
            if self.percentage < -100 or self.percentage > 1000:
                raise InvalidInvestmentException(
                    "Yield percentage should be between -100 and 1000%"
                )

    @property
    def is_positive(self) -> bool:
        return self.amount > 0

    @property
    def is_negative(self) -> bool:
        return self.amount < 0

    def __str__(self) -> str:
        if self.percentage is not None:
            return f"{self.amount} ({self.percentage:.2f}%)"
        return str(self.amount)
