"""Validation service - domain business rule validations."""

from datetime import datetime
from decimal import Decimal

from app.domain.value_objects import Identifier, Money, Quantity, InvestmentType
from app.domain.exceptions import (
    InvalidIdentifierException,
    InvalidTransactionException,
    InvalidInvestmentException,
)


class ValidationService:
    """
    Stateless service for domain-level validations.
    Enforces business rules and constraints.
    """

    @staticmethod
    def validate_identifier_format(
        identifier_value: str,
        identifier_type: str,
    ) -> None:
        """Validate that identifier matches required format."""
        try:
            if identifier_type.upper() == "ISIN":
                Identifier.create_isin(identifier_value)
            elif identifier_type.upper() == "TICKER":
                Identifier.create_ticker(identifier_value)
            else:
                raise InvalidIdentifierException(
                    identifier_value,
                    f"Unknown identifier type: {identifier_type}",
                )
        except InvalidIdentifierException:
            raise

    @staticmethod
    def validate_transaction_amount(amount: Decimal) -> None:
        """Validate transaction amount is positive."""
        if amount <= 0:
            raise InvalidTransactionException(
                f"Amount must be positive, got {amount}"
            )

    @staticmethod
    def validate_transaction_quantity(quantity: Decimal) -> None:
        """Validate transaction quantity is positive."""
        if quantity <= 0:
            raise InvalidTransactionException(
                f"Quantity must be positive, got {quantity}"
            )

    @staticmethod
    def validate_transaction_broker(broker: str) -> None:
        """Validate broker name is provided and valid."""
        if not broker or len(broker.strip()) == 0:
            raise InvalidTransactionException("Broker name is required")
        if len(broker) > 100:
            raise InvalidTransactionException(
                "Broker name must be less than 100 characters"
            )

    @staticmethod
    def validate_transaction_date(date: datetime) -> None:
        """Validate transaction date is not in the future."""
        if date > datetime.utcnow():
            raise InvalidTransactionException(
                f"Transaction date cannot be in the future"
            )

    @staticmethod
    def validate_price_is_positive(price: Decimal) -> None:
        """Validate price is positive."""
        if price <= 0:
            raise InvalidInvestmentException(
                f"Price must be positive, got {price}"
            )

    @staticmethod
    def validate_price_date(date: datetime) -> None:
        """Validate price date is not in the future."""
        if date > datetime.utcnow():
            raise InvalidInvestmentException(
                "Price date cannot be in the future"
            )

    @staticmethod
    def validate_portfolio_name(name: str) -> None:
        """Validate portfolio name."""
        if not name or len(name.strip()) < 2:
            raise ValueError("Portfolio name must be at least 2 characters")
        if len(name) > 100:
            raise ValueError("Portfolio name must be less than 100 characters")

    @staticmethod
    def validate_investment_type(investment_type: str) -> InvestmentType:
        """Validate and return investment type enum."""
        try:
            return InvestmentType(investment_type.lower())
        except ValueError:
            valid_types = ", ".join([t.value for t in InvestmentType])
            raise InvalidInvestmentException(
                f"Invalid investment type '{investment_type}'. "
                f"Must be one of: {valid_types}"
            )

    @staticmethod
    def validate_username(username: str) -> None:
        """Validate username format."""
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(username) > 50:
            raise ValueError("Username must be less than 50 characters")
        if not username.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username must be alphanumeric (with _ and - allowed)"
            )

    @staticmethod
    def validate_email(email: str) -> None:
        """Basic email validation."""
        if not email or "@" not in email or "." not in email:
            raise ValueError("Invalid email address")
        if len(email) > 100:
            raise ValueError("Email must be less than 100 characters")
