"""Tests for domain value objects."""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from app.domain.value_objects import (
    Identifier,
    Money,
    Quantity,
    Yield,
    InvestmentType,
)
from app.domain.exceptions import (
    InvalidIdentifierException,
    InvalidTransactionException,
    InvalidInvestmentException,
)


class TestIdentifier:
    """Test ISIN and ticker identifier validation."""

    def test_create_valid_isin(self):
        """Test creating a valid ISIN identifier."""
        identifier = Identifier.create_isin("US0378331005")
        assert identifier.value == "US0378331005"
        assert identifier.identifier_type == "ISIN"

    def test_create_valid_ticker(self):
        """Test creating a valid ticker identifier."""
        identifier = Identifier.create_ticker("AAPL")
        assert identifier.value == "AAPL"
        assert identifier.identifier_type == "TICKER"

    def test_isin_too_short(self):
        """Test ISIN validation rejects short identifiers."""
        with pytest.raises(InvalidIdentifierException):
            Identifier.create_isin("US037")

    def test_isin_invalid_format(self):
        """Test ISIN validation rejects invalid format."""
        with pytest.raises(InvalidIdentifierException):
            Identifier.create_isin("INVALID1234567")

    def test_ticker_too_long(self):
        """Test ticker validation rejects long identifiers."""
        with pytest.raises(InvalidIdentifierException):
            Identifier.create_ticker("TOOLONG")

    def test_ticker_with_invalid_chars(self):
        """Test ticker validation rejects non-alphanumeric."""
        with pytest.raises(InvalidIdentifierException):
            Identifier.create_ticker("AA-PL")

    def test_identifier_immutable(self):
        """Test that identifiers are immutable."""
        identifier = Identifier.create_isin("US0378331005")
        with pytest.raises(AttributeError):
            identifier.value = "DIFFERENT"


class TestMoney:
    """Test Money value object."""

    def test_create_valid_money(self):
        """Test creating valid money."""
        money = Money(Decimal("100.50"), "USD")
        assert money.amount == Decimal("100.50")
        assert money.currency == "USD"

    def test_negative_money_allowed_for_losses(self):
        """Test that negative monetary values are allowed for losses."""
        money = Money(Decimal("-100"), "USD")
        assert money.amount == Decimal("-100")
        assert money.currency == "USD"

    def test_add_money(self):
        """Test adding money."""
        m1 = Money(Decimal("100"), "USD")
        m2 = Money(Decimal("50"), "USD")
        result = m1 + m2
        assert result.amount == Decimal("150")

    def test_subtract_money(self):
        """Test subtracting money."""
        m1 = Money(Decimal("100"), "USD")
        m2 = Money(Decimal("30"), "USD")
        result = m1 - m2
        assert result.amount == Decimal("70")

    def test_multiply_money(self):
        """Test multiplying money."""
        m = Money(Decimal("100"), "USD")
        result = m * 2
        assert result.amount == Decimal("200")

    def test_add_different_currencies_fails(self):
        """Test adding money with different currencies fails."""
        m1 = Money(Decimal("100"), "USD")
        m2 = Money(Decimal("50"), "EUR")
        with pytest.raises(InvalidTransactionException):
            m1 + m2

    def test_is_zero(self):
        """Test zero detection."""
        m_zero = Money(Decimal("0"), "USD")
        m_nonzero = Money(Decimal("100"), "USD")
        assert m_zero.is_zero
        assert not m_nonzero.is_zero


class TestQuantity:
    """Test Quantity value object."""

    def test_create_valid_quantity(self):
        """Test creating valid quantity."""
        qty = Quantity(Decimal("100"))
        assert qty.value == Decimal("100")

    def test_zero_quantity_rejected(self):
        """Test that zero quantity is rejected."""
        with pytest.raises(InvalidTransactionException):
            Quantity(Decimal("0"))

    def test_negative_quantity_rejected(self):
        """Test that negative quantity is rejected."""
        with pytest.raises(InvalidTransactionException):
            Quantity(Decimal("-50"))

    def test_add_quantities(self):
        """Test adding quantities."""
        q1 = Quantity(Decimal("100"))
        q2 = Quantity(Decimal("50"))
        result = q1 + q2
        assert result.value == Decimal("150")

    def test_multiply_quantity(self):
        """Test multiplying quantity."""
        q = Quantity(Decimal("100"))
        result = q * 2
        assert result.value == Decimal("200")


class TestYield:
    """Test Yield value object."""

    def test_positive_yield(self):
        """Test positive yield."""
        y = Yield(Decimal("100"))
        assert y.is_positive
        assert not y.is_negative

    def test_negative_yield(self):
        """Test negative yield."""
        y = Yield(Decimal("-50"))
        assert not y.is_positive
        assert y.is_negative

    def test_zero_yield(self):
        """Test zero yield."""
        y = Yield(Decimal("0"))
        assert not y.is_positive
        assert not y.is_negative

    def test_yield_with_percentage(self):
        """Test yield with percentage."""
        y = Yield(Decimal("100"), Decimal("50.5"))
        assert y.amount == Decimal("100")
        assert y.percentage == Decimal("50.5")


class TestInvestmentType:
    """Test InvestmentType enum."""

    def test_valid_types(self):
        """Test valid investment types."""
        assert InvestmentType.STOCK.value == "stock"
        assert InvestmentType.BOND.value == "bond"
        assert InvestmentType.ETF.value == "etf"
        assert InvestmentType.CRYPTO.value == "crypto"

    def test_can_iterate_types(self):
        """Test iterating over investment types."""
        types = list(InvestmentType)
        assert len(types) >= 5
