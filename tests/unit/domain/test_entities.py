"""Tests for domain entities."""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

from app.domain.entities.user import User
from app.domain.entities.portfolio import Portfolio
from app.domain.entities.investment import Investment
from app.domain.entities.transaction import Transaction
from app.domain.entities.price_history import PriceHistory
from app.domain.value_objects import (
    Identifier,
    Money,
    Quantity,
    InvestmentType,
)


class TestUserEntity:
    """Test User entity."""

    def test_create_valid_user(self):
        """Test creating a valid user."""
        user = User(
            id="user-123",
            username="john_doe",
            email="john@example.com",
            created_at=datetime.utcnow(),
        )
        assert user.id == "user-123"
        assert user.username == "john_doe"
        assert user.email == "john@example.com"

    def test_username_too_short_rejected(self):
        """Test that short usernames are rejected."""
        with pytest.raises(ValueError):
            User(
                id="user-123",
                username="ab",
                email="ab@example.com",
                created_at=datetime.utcnow(),
            )

    def test_invalid_email_rejected(self):
        """Test that invalid emails are rejected."""
        with pytest.raises(ValueError):
            User(
                id="user-123",
                username="john_doe",
                email="invalid-email",
                created_at=datetime.utcnow(),
            )


class TestPortfolioEntity:
    """Test Portfolio entity."""

    def test_create_valid_portfolio(self):
        """Test creating a valid portfolio."""
        portfolio = Portfolio(
            id="port-123",
            user_id="user-123",
            name="My Portfolio",
            description="Test portfolio",
            created_at=datetime.utcnow(),
        )
        assert portfolio.id == "port-123"
        assert portfolio.user_id == "user-123"
        assert portfolio.name == "My Portfolio"

    def test_name_too_short_rejected(self):
        """Test that short names are rejected."""
        with pytest.raises(ValueError):
            Portfolio(
                id="port-123",
                user_id="user-123",
                name="X",
                created_at=datetime.utcnow(),
            )

    def test_update_portfolio_details(self):
        """Test updating portfolio details."""
        portfolio = Portfolio(
            id="port-123",
            user_id="user-123",
            name="Old Name",
            created_at=datetime.utcnow(),
        )
        portfolio.update_details(
            name="New Name", description="Updated", updated_at=datetime.utcnow()
        )
        assert portfolio.name == "New Name"
        assert portfolio.description == "Updated"
        assert portfolio.updated_at is not None


class TestInvestmentEntity:
    """Test Investment entity."""

    def test_create_valid_investment(self):
        """Test creating a valid investment."""
        identifier = Identifier.create_isin("US0378331005")
        investment = Investment(
            id="inv-123",
            portfolio_id="port-123",
            identifier=identifier,
            type=InvestmentType.STOCK,
            created_at=datetime.utcnow(),
        )
        assert investment.id == "inv-123"
        assert investment.identifier.value == "US0378331005"
        assert investment.type == InvestmentType.STOCK

    def test_update_investment_type(self):
        """Test updating investment type."""
        identifier = Identifier.create_ticker("AAPL")
        investment = Investment(
            id="inv-123",
            portfolio_id="port-123",
            identifier=identifier,
            type=InvestmentType.STOCK,
            created_at=datetime.utcnow(),
        )
        investment.update_details(type=InvestmentType.ETF, updated_at=datetime.utcnow())
        assert investment.type == InvestmentType.ETF


class TestTransactionEntity:
    """Test Transaction entity."""

    def test_create_valid_transaction(self):
        """Test creating a valid transaction."""
        transaction = Transaction(
            id="tx-123",
            investment_id="inv-123",
            amount=Money(Decimal("1000"), "USD"),
            quantity=Quantity(Decimal("10")),
            broker="Interactive Brokers",
            date=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert transaction.id == "tx-123"
        assert transaction.broker == "Interactive Brokers"

    def test_price_per_unit(self):
        """Test price per unit calculation."""
        transaction = Transaction(
            id="tx-123",
            investment_id="inv-123",
            amount=Money(Decimal("1000"), "USD"),
            quantity=Quantity(Decimal("10")),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert transaction.price_per_unit == Decimal("100")

    def test_future_date_rejected(self):
        """Test that future transaction dates are rejected."""
        with pytest.raises(ValueError):
            Transaction(
                id="tx-123",
                investment_id="inv-123",
                amount=Money(Decimal("1000"), "USD"),
                quantity=Quantity(Decimal("10")),
                broker="Broker",
                date=datetime.utcnow() + timedelta(days=1),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

    def test_update_transaction(self):
        """Test updating transaction details."""
        transaction = Transaction(
            id="tx-123",
            investment_id="inv-123",
            amount=Money(Decimal("1000"), "USD"),
            quantity=Quantity(Decimal("10")),
            broker="Old Broker",
            date=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        transaction.update_details(
            broker="New Broker", updated_at=datetime.utcnow()
        )
        assert transaction.broker == "New Broker"


class TestPriceHistoryEntity:
    """Test PriceHistory entity."""

    def test_create_valid_price_history(self):
        """Test creating a valid price history record."""
        price_history = PriceHistory(
            id="ph-123",
            investment_id="inv-123",
            price=Money(Decimal("150.50"), "USD"),
            date=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
        )
        assert price_history.id == "ph-123"
        assert price_history.price.amount == Decimal("150.50")

    def test_zero_price_rejected(self):
        """Test that zero price is rejected."""
        with pytest.raises(ValueError):
            PriceHistory(
                id="ph-123",
                investment_id="inv-123",
                price=Money(Decimal("0"), "USD"),
                date=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )

    def test_future_date_rejected(self):
        """Test that future price dates are rejected."""
        with pytest.raises(ValueError):
            PriceHistory(
                id="ph-123",
                investment_id="inv-123",
                price=Money(Decimal("100"), "USD"),
                date=datetime.utcnow() + timedelta(days=1),
                created_at=datetime.utcnow(),
            )
