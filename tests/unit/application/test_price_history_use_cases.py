"""Tests for price history use cases."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.application.use_cases.price_history_use_cases import PriceHistoryUseCases
from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.portfolio_use_cases import PortfolioUseCases
from app.application.use_cases.user_use_cases import UserUseCases
from app.application.dto.price_history_dto import CreatePriceHistoryDTO
from app.application.dto.investment_dto import CreateInvestmentDTO
from app.application.dto.portfolio_dto import CreatePortfolioDTO
from app.application.dto.user_dto import CreateUserDTO
from app.domain.exceptions import (
    EntityNotFoundException,
    UnauthorizedException,
)
from tests.infrastructure.in_memory_repositories import (
    InMemoryPriceHistoryRepository,
    InMemoryInvestmentRepository,
    InMemoryPortfolioRepository,
    InMemoryUserRepository,
)


class TestPriceHistoryUseCases:
    """Test price history use cases."""

    @pytest.fixture
    def repos(self):
        return {
            "user": InMemoryUserRepository(),
            "portfolio": InMemoryPortfolioRepository(),
            "investment": InMemoryInvestmentRepository(),
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
            "price_history": PriceHistoryUseCases(
                repos["price_history"],
                repos["investment"],
                repos["portfolio"],
            ),
        }

    @pytest.fixture
    def setup_user_portfolio_investment(self, use_cases):
        """Create user, portfolio, and investment."""
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

        investment_dto = CreateInvestmentDTO(
            portfolio_id=portfolio.id,
            identifier="AAPL",
            identifier_type="TICKER",
            type="stock",
        )
        investment = use_cases["investment"].create_investment(
            user.id, investment_dto
        )

        return user.id, portfolio.id, investment.id

    def test_record_price_success(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test recording a price."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        dto = CreatePriceHistoryDTO(
            investment_id=investment_id,
            price=Decimal("150.50"),
            date=datetime.utcnow() - timedelta(days=1),
        )
        result = use_cases["price_history"].record_price(user_id, dto)

        assert result.id is not None
        assert result.price == Decimal("150.50")
        assert result.investment_id == investment_id

    def test_record_price_invalid_price(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test that zero price fails."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        dto = CreatePriceHistoryDTO(
            investment_id=investment_id,
            price=Decimal("0"),
            date=datetime.utcnow() - timedelta(days=1),
        )
        with pytest.raises(Exception):  # InvalidInvestmentException
            use_cases["price_history"].record_price(user_id, dto)

    def test_record_price_future_date(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test that future date fails."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        dto = CreatePriceHistoryDTO(
            investment_id=investment_id,
            price=Decimal("150.50"),
            date=datetime.utcnow() + timedelta(days=1),
        )
        with pytest.raises(Exception):  # InvalidInvestmentException
            use_cases["price_history"].record_price(user_id, dto)

    def test_get_latest_price_success(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test getting latest price."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        dto1 = CreatePriceHistoryDTO(
            investment_id=investment_id,
            price=Decimal("150.00"),
            date=datetime.utcnow() - timedelta(days=2),
        )
        dto2 = CreatePriceHistoryDTO(
            investment_id=investment_id,
            price=Decimal("155.50"),
            date=datetime.utcnow() - timedelta(days=1),
        )

        use_cases["price_history"].record_price(user_id, dto1)
        use_cases["price_history"].record_price(user_id, dto2)

        result = use_cases["price_history"].get_latest_price(
            investment_id, user_id
        )

        assert result is not None
        assert result.price == Decimal("155.50")  # Most recent

    def test_get_latest_price_none_exist(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test getting latest price when none exist."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        result = use_cases["price_history"].get_latest_price(
            investment_id, user_id
        )
        assert result is None

    def test_list_prices(self, use_cases, setup_user_portfolio_investment):
        """Test listing all prices."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        dto1 = CreatePriceHistoryDTO(
            investment_id=investment_id,
            price=Decimal("150.00"),
            date=datetime.utcnow() - timedelta(days=2),
        )
        dto2 = CreatePriceHistoryDTO(
            investment_id=investment_id,
            price=Decimal("155.50"),
            date=datetime.utcnow() - timedelta(days=1),
        )

        use_cases["price_history"].record_price(user_id, dto1)
        use_cases["price_history"].record_price(user_id, dto2)

        result = use_cases["price_history"].list_prices(
            investment_id, user_id
        )

        assert len(result) == 2

    def test_list_prices_by_date_range(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test listing prices within date range."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        base_date = datetime.utcnow()
        dto1 = CreatePriceHistoryDTO(
            investment_id=investment_id,
            price=Decimal("150.00"),
            date=base_date - timedelta(days=10),
        )
        dto2 = CreatePriceHistoryDTO(
            investment_id=investment_id,
            price=Decimal("155.50"),
            date=base_date - timedelta(days=5),
        )
        dto3 = CreatePriceHistoryDTO(
            investment_id=investment_id,
            price=Decimal("160.00"),
            date=base_date - timedelta(days=1),
        )

        use_cases["price_history"].record_price(user_id, dto1)
        use_cases["price_history"].record_price(user_id, dto2)
        use_cases["price_history"].record_price(user_id, dto3)

        # Query range that includes only dto2 and dto3
        result = use_cases["price_history"].list_prices_by_date_range(
            investment_id,
            user_id,
            base_date - timedelta(days=7),
            base_date,
        )

        assert len(result) == 2
