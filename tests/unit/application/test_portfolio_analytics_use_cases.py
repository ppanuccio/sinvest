"""Tests for portfolio analytics use cases."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.application.use_cases.portfolio_analytics_use_cases import (
    PortfolioAnalyticsUseCases,
)
from app.application.use_cases.portfolio_use_cases import PortfolioUseCases
from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.transaction_use_cases import TransactionUseCases
from app.application.use_cases.price_history_use_cases import PriceHistoryUseCases
from app.application.use_cases.user_use_cases import UserUseCases
from app.application.dto.portfolio_dto import CreatePortfolioDTO
from app.application.dto.investment_dto import CreateInvestmentDTO
from app.application.dto.transaction_dto import CreateTransactionDTO
from app.application.dto.price_history_dto import CreatePriceHistoryDTO
from app.application.dto.user_dto import CreateUserDTO
from app.domain.exceptions import UnauthorizedException
from tests.infrastructure.in_memory_repositories import (
    InMemoryPortfolioRepository,
    InMemoryInvestmentRepository,
    InMemoryTransactionRepository,
    InMemoryPriceHistoryRepository,
    InMemoryUserRepository,
)


class TestPortfolioAnalyticsUseCases:
    """Test portfolio analytics use cases."""

    @pytest.fixture
    def repos(self):
        return {
            "user": InMemoryUserRepository(),
            "portfolio": InMemoryPortfolioRepository(),
            "investment": InMemoryInvestmentRepository(),
            "transaction": InMemoryTransactionRepository(),
            "price_history": InMemoryPriceHistoryRepository(),
        }

    @pytest.fixture
    def use_cases(self, repos):
        return {
            "user": UserUseCases(repos["user"]),
            "portfolio": PortfolioUseCases(repos["portfolio"]),
            "investment": InvestmentUseCases(
                repos["investment"], repos["portfolio"]
            ),
            "transaction": TransactionUseCases(
                repos["transaction"],
                repos["investment"],
                repos["portfolio"],
            ),
            "price_history": PriceHistoryUseCases(
                repos["price_history"],
                repos["investment"],
                repos["portfolio"],
            ),
            "analytics": PortfolioAnalyticsUseCases(
                repos["portfolio"],
                repos["investment"],
                repos["transaction"],
                repos["price_history"],
            ),
        }

    @pytest.fixture
    def setup_portfolio_with_data(self, use_cases):
        """Create a portfolio with investments, transactions, and prices."""
        # Create user
        user_dto = CreateUserDTO(
            username="test_user",
            email="test@example.com",
            password="password123",
        )
        user = use_cases["user"].create_user(user_dto)

        # Create portfolio
        portfolio_dto = CreatePortfolioDTO(
            user_id=user.id,
            name="Test Portfolio",
        )
        portfolio = use_cases["portfolio"].create_portfolio(
            user.id, portfolio_dto
        )

        # Create investment
        investment_dto = CreateInvestmentDTO(
            portfolio_id=portfolio.id,
            identifier="AAPL",
            identifier_type="TICKER",
            type="stock",
        )
        investment = use_cases["investment"].create_investment(
            user.id, investment_dto
        )

        # Create transaction (buy 10 shares at $100)
        tx_dto = CreateTransactionDTO(
            investment_id=investment.id,
            amount=Decimal("1000"),
            quantity=Decimal("10"),
            broker="Broker1",
            date=datetime.utcnow() - timedelta(days=10),
        )
        use_cases["transaction"].create_transaction(user.id, tx_dto)

        # Record price (current price: $150)
        price_dto = CreatePriceHistoryDTO(
            investment_id=investment.id,
            price=Decimal("150"),
            date=datetime.utcnow() - timedelta(days=1),
        )
        use_cases["price_history"].record_price(user.id, price_dto)

        return user.id, portfolio.id, investment.id

    def test_get_portfolio_analytics_success(
        self, use_cases, setup_portfolio_with_data
    ):
        """Test getting portfolio analytics."""
        user_id, portfolio_id, investment_id = setup_portfolio_with_data

        result = use_cases["analytics"].get_portfolio_analytics(
            portfolio_id, user_id
        )

        assert result.portfolio_id == portfolio_id
        assert result.total_value > 0  # (150 * 10) - 1000 = 500
        assert result.total_invested == Decimal("1000")
        assert result.total_yield > 0  # 500
        assert len(result.investments) == 1

    def test_portfolio_analytics_calculations(
        self, use_cases, setup_portfolio_with_data
    ):
        """Test that analytics calculations are correct."""
        user_id, portfolio_id, investment_id = setup_portfolio_with_data

        result = use_cases["analytics"].get_portfolio_analytics(
            portfolio_id, user_id
        )

        # Verify calculations
        # Buy 10 @ $100 = $1000 invested
        # Current price $150 = $1500 total value
        # Profit = 1500 - 1000 = 500
        # Yield % = 500 / 1000 = 50%
        assert result.total_invested == Decimal("1000")
        assert result.total_value == Decimal("500")  # Net value after cost
        assert result.total_yield == Decimal("500")
        assert result.total_yield_percentage == Decimal("50")

    def test_portfolio_analytics_allocation(
        self, use_cases, setup_portfolio_with_data
    ):
        """Test allocation percentage calculation."""
        user_id, portfolio_id, investment_id = setup_portfolio_with_data

        result = use_cases["analytics"].get_portfolio_analytics(
            portfolio_id, user_id
        )

        # Single investment = 100% allocation
        assert result.allocation[investment_id] == Decimal("100")

    def test_portfolio_analytics_unauthorized(
        self, use_cases, setup_portfolio_with_data
    ):
        """Test that unauthorized user cannot access analytics."""
        user_id, portfolio_id, investment_id = setup_portfolio_with_data

        with pytest.raises(UnauthorizedException):
            use_cases["analytics"].get_portfolio_analytics(
                portfolio_id, "different-user"
            )

    def test_portfolio_analytics_multiple_investments(self, use_cases):
        """Test analytics with multiple investments."""
        # Create user and portfolio
        user_dto = CreateUserDTO(
            username="test_user",
            email="test@example.com",
            password="password123",
        )
        user = use_cases["user"].create_user(user_dto)

        portfolio_dto = CreatePortfolioDTO(
            user_id=user.id,
            name="Test Portfolio",
        )
        portfolio = use_cases["portfolio"].create_portfolio(
            user.id, portfolio_dto
        )

        # Create first investment
        inv1_dto = CreateInvestmentDTO(
            portfolio_id=portfolio.id,
            identifier="AAPL",
            identifier_type="TICKER",
            type="stock",
        )
        inv1 = use_cases["investment"].create_investment(user.id, inv1_dto)

        # Create second investment
        inv2_dto = CreateInvestmentDTO(
            portfolio_id=portfolio.id,
            identifier="GOOGL",
            identifier_type="TICKER",
            type="stock",
        )
        inv2 = use_cases["investment"].create_investment(user.id, inv2_dto)

        # Create transactions
        tx1_dto = CreateTransactionDTO(
            investment_id=inv1.id,
            amount=Decimal("1000"),
            quantity=Decimal("10"),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
        )
        use_cases["transaction"].create_transaction(user.id, tx1_dto)

        tx2_dto = CreateTransactionDTO(
            investment_id=inv2.id,
            amount=Decimal("2000"),
            quantity=Decimal("20"),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
        )
        use_cases["transaction"].create_transaction(user.id, tx2_dto)

        # Record prices
        price1_dto = CreatePriceHistoryDTO(
            investment_id=inv1.id,
            price=Decimal("150"),
            date=datetime.utcnow() - timedelta(days=1),
        )
        use_cases["price_history"].record_price(user.id, price1_dto)

        price2_dto = CreatePriceHistoryDTO(
            investment_id=inv2.id,
            price=Decimal("150"),
            date=datetime.utcnow() - timedelta(days=1),
        )
        use_cases["price_history"].record_price(user.id, price2_dto)

        # Get analytics
        result = use_cases["analytics"].get_portfolio_analytics(
            portfolio.id, user.id
        )

        # Verify
        assert len(result.investments) == 2
        assert result.total_invested == Decimal("3000")
        # (150*10 - 1000) + (150*20 - 2000) = 500 + 1000 = 1500
        assert result.total_value == Decimal("1500")
        assert result.total_yield == Decimal("1500")
        # 1500 / 3000 = 50%
        assert result.total_yield_percentage == Decimal("50")
