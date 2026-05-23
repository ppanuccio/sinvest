"""Tests for domain services."""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from app.domain.services.investment_calculation_service import (
    InvestmentCalculationService,
)
from app.domain.services.portfolio_calculation_service import (
    PortfolioCalculationService,
)
from app.domain.entities.transaction import Transaction
from app.domain.entities.investment import Investment
from app.domain.entities.price_history import PriceHistory
from app.domain.value_objects import (
    Money,
    Quantity,
    Identifier,
    InvestmentType,
    Yield,
)


class TestInvestmentCalculationService:
    """Test investment calculation service."""

    def test_calculate_total_quantity_single_transaction(self):
        """Test calculating total quantity with single transaction."""
        tx = Transaction(
            id="tx-1",
            investment_id="inv-1",
            amount=Money(Decimal("1000"), "USD"),
            quantity=Quantity(Decimal("10")),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        result = InvestmentCalculationService.calculate_total_quantity([tx])
        assert result == Decimal("10")

    def test_calculate_total_quantity_multiple_transactions(self):
        """Test calculating total quantity with multiple transactions."""
        tx1 = Transaction(
            id="tx-1",
            investment_id="inv-1",
            amount=Money(Decimal("1000"), "USD"),
            quantity=Quantity(Decimal("10")),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=2),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        tx2 = Transaction(
            id="tx-2",
            investment_id="inv-1",
            amount=Money(Decimal("500"), "USD"),
            quantity=Quantity(Decimal("5")),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        result = InvestmentCalculationService.calculate_total_quantity(
            [tx1, tx2]
        )
        assert result == Decimal("15")

    def test_calculate_total_quantity_empty(self):
        """Test calculating total quantity with no transactions."""
        result = InvestmentCalculationService.calculate_total_quantity([])
        assert result == Decimal("0")

    def test_calculate_initial_amount(self):
        """Test extracting initial amount from first transaction."""
        tx1 = Transaction(
            id="tx-1",
            investment_id="inv-1",
            amount=Money(Decimal("1000"), "USD"),
            quantity=Quantity(Decimal("10")),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=2),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        tx2 = Transaction(
            id="tx-2",
            investment_id="inv-1",
            amount=Money(Decimal("500"), "USD"),
            quantity=Quantity(Decimal("5")),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        result = InvestmentCalculationService.calculate_initial_amount(
            [tx1, tx2]
        )
        assert result.amount == Decimal("1000")

    def test_calculate_total_invested_amount(self):
        """Test calculating total amount invested."""
        tx1 = Transaction(
            id="tx-1",
            investment_id="inv-1",
            amount=Money(Decimal("1000"), "USD"),
            quantity=Quantity(Decimal("10")),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=2),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        tx2 = Transaction(
            id="tx-2",
            investment_id="inv-1",
            amount=Money(Decimal("500"), "USD"),
            quantity=Quantity(Decimal("5")),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        result = InvestmentCalculationService.calculate_total_invested_amount(
            [tx1, tx2]
        )
        assert result.amount == Decimal("1500")

    def test_calculate_total_value_profit_scenario(self):
        """Test total value calculation with profit."""
        # Buy 10 shares at $100 each = $1000
        # Current price = $150
        # Total value = (150 * 10) - 1000 = 1500 - 1000 = 500 (profit)
        tx = Transaction(
            id="tx-1",
            investment_id="inv-1",
            amount=Money(Decimal("1000"), "USD"),
            quantity=Quantity(Decimal("10")),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        current_price = Money(Decimal("150"), "USD")
        result = InvestmentCalculationService.calculate_total_value(
            [tx], current_price
        )
        assert result.amount == Decimal("500")

    def test_calculate_total_value_loss_scenario(self):
        """Test total value calculation with loss."""
        # Buy 10 shares at $100 each = $1000
        # Current price = $80
        # Total value = (80 * 10) - 1000 = 800 - 1000 = -200 (loss)
        tx = Transaction(
            id="tx-1",
            investment_id="inv-1",
            amount=Money(Decimal("1000"), "USD"),
            quantity=Quantity(Decimal("10")),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        current_price = Money(Decimal("80"), "USD")
        result = InvestmentCalculationService.calculate_total_value(
            [tx], current_price
        )
        assert result.amount == Decimal("-200")

    def test_calculate_yield_positive(self):
        """Test yield calculation with positive return."""
        total_value = Money(Decimal("500"), "USD")
        initial_amount = Money(Decimal("1000"), "USD")
        result = InvestmentCalculationService.calculate_yield(
            total_value, initial_amount
        )
        assert result.amount == Decimal("500")
        assert result.is_positive

    def test_calculate_yield_negative(self):
        """Test yield calculation with negative return."""
        total_value = Money(Decimal("-200"), "USD")
        initial_amount = Money(Decimal("1000"), "USD")
        result = InvestmentCalculationService.calculate_yield(
            total_value, initial_amount
        )
        assert result.amount == Decimal("-200")
        assert result.is_negative

    def test_calculate_yield_percentage(self):
        """Test yield percentage calculation."""
        # Invested $1000, gained $500 = 50% return
        yield_value = Yield(Decimal("500"))
        initial_amount = Money(Decimal("1000"), "USD")
        result = InvestmentCalculationService.calculate_yield_percentage(
            yield_value, initial_amount
        )
        assert result == Decimal("50")

    def test_calculate_yield_percentage_negative(self):
        """Test yield percentage with negative return."""
        # Invested $1000, lost $200 = -20% return
        yield_value = Yield(Decimal("-200"))
        initial_amount = Money(Decimal("1000"), "USD")
        result = InvestmentCalculationService.calculate_yield_percentage(
            yield_value, initial_amount
        )
        assert result == Decimal("-20")


class TestPortfolioCalculationService:
    """Test portfolio calculation service."""

    def test_calculate_portfolio_totals_empty(self):
        """Test portfolio totals with no investments."""
        total_value, total_invested, total_yield, total_yield_pct = (
            PortfolioCalculationService.calculate_portfolio_totals(
                [], {}, {}
            )
        )
        assert total_value.amount == Decimal("0")
        assert total_invested.amount == Decimal("0")
        assert total_yield.amount == Decimal("0")

    def test_calculate_allocation_percentages_empty(self):
        """Test allocation with no investments."""
        allocation = PortfolioCalculationService.calculate_allocation_percentages(
            [], {}, {}
        )
        assert allocation == {}

    def test_calculate_allocation_single_investment(self):
        """Test allocation with single investment (100%)."""
        identifier = Identifier.create_ticker("AAPL")
        investment = Investment(
            id="inv-1",
            portfolio_id="port-1",
            identifier=identifier,
            type=InvestmentType.STOCK,
            created_at=datetime.utcnow(),
        )

        tx = Transaction(
            id="tx-1",
            investment_id="inv-1",
            amount=Money(Decimal("1000"), "USD"),
            quantity=Quantity(Decimal("10")),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        price = PriceHistory(
            id="ph-1",
            investment_id="inv-1",
            price=Money(Decimal("150"), "USD"),
            date=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
        )

        allocation = PortfolioCalculationService.calculate_allocation_percentages(
            [investment],
            {"inv-1": [tx]},
            {"inv-1": [price]},
        )

        assert "inv-1" in allocation
        assert allocation["inv-1"] == Decimal("100")
