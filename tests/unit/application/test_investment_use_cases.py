"""Tests for investment use cases."""

import pytest
from datetime import datetime

from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.portfolio_use_cases import PortfolioUseCases
from app.application.use_cases.user_use_cases import UserUseCases
from app.application.dto.investment_dto import (
    CreateInvestmentDTO,
    UpdateInvestmentDTO,
)
from app.application.dto.portfolio_dto import CreatePortfolioDTO
from app.application.dto.user_dto import CreateUserDTO
from app.domain.exceptions import (
    EntityNotFoundException,
    UnauthorizedException,
    InvalidIdentifierException,
)
from tests.infrastructure.in_memory_repositories import (
    InMemoryInvestmentRepository,
    InMemoryPortfolioRepository,
    InMemoryUserRepository,
)


class TestInvestmentUseCases:
    """Test investment use cases."""

    @pytest.fixture
    def user_repo(self):
        return InMemoryUserRepository()

    @pytest.fixture
    def portfolio_repo(self):
        return InMemoryPortfolioRepository()

    @pytest.fixture
    def investment_repo(self):
        return InMemoryInvestmentRepository()

    @pytest.fixture
    def user_use_cases(self, user_repo):
        return UserUseCases(user_repo)

    @pytest.fixture
    def portfolio_use_cases(self, portfolio_repo):
        return PortfolioUseCases(portfolio_repo)

    @pytest.fixture
    def investment_use_cases(
        self, investment_repo, portfolio_repo
    ):
        return InvestmentUseCases(investment_repo, portfolio_repo)

    @pytest.fixture
    def setup_user_and_portfolio(
        self, user_use_cases, portfolio_use_cases
    ):
        """Create user and portfolio for testing."""
        user_dto = CreateUserDTO(
            username="test_user",
            email="test@example.com",
            password="password123",
        )
        user = user_use_cases.create_user(user_dto)

        portfolio_dto = CreatePortfolioDTO(
            user_id=user.id,
            name="Test Portfolio",
        )
        portfolio = portfolio_use_cases.create_portfolio(user.id, portfolio_dto)

        return user.id, portfolio.id

    def test_create_investment_with_isin(
        self, investment_use_cases, setup_user_and_portfolio
    ):
        """Test creating investment with ISIN identifier."""
        user_id, portfolio_id = setup_user_and_portfolio

        dto = CreateInvestmentDTO(
            portfolio_id=portfolio_id,
            identifier="US0378331005",
            identifier_type="ISIN",
            type="stock",
        )
        result = investment_use_cases.create_investment(user_id, dto)

        assert result.id is not None
        assert result.identifier == "US0378331005"
        assert result.identifier_type == "ISIN"
        assert result.type == "stock"

    def test_create_investment_with_ticker(
        self, investment_use_cases, setup_user_and_portfolio
    ):
        """Test creating investment with ticker."""
        user_id, portfolio_id = setup_user_and_portfolio

        dto = CreateInvestmentDTO(
            portfolio_id=portfolio_id,
            identifier="AAPL",
            identifier_type="TICKER",
            type="stock",
        )
        result = investment_use_cases.create_investment(user_id, dto)

        assert result.identifier == "AAPL"
        assert result.identifier_type == "TICKER"

    def test_create_investment_invalid_isin(
        self, investment_use_cases, setup_user_and_portfolio
    ):
        """Test creating investment with invalid ISIN."""
        user_id, portfolio_id = setup_user_and_portfolio

        dto = CreateInvestmentDTO(
            portfolio_id=portfolio_id,
            identifier="INVALID",
            identifier_type="ISIN",
            type="stock",
        )
        with pytest.raises(InvalidIdentifierException):
            investment_use_cases.create_investment(user_id, dto)

    def test_create_investment_invalid_type(
        self, investment_use_cases, setup_user_and_portfolio
    ):
        """Test creating investment with invalid type."""
        user_id, portfolio_id = setup_user_and_portfolio

        dto = CreateInvestmentDTO(
            portfolio_id=portfolio_id,
            identifier="AAPL",
            identifier_type="TICKER",
            type="invalid_type",
        )
        with pytest.raises(Exception):  # InvalidInvestmentException
            investment_use_cases.create_investment(user_id, dto)

    def test_get_investment_success(
        self, investment_use_cases, setup_user_and_portfolio
    ):
        """Test retrieving an investment."""
        user_id, portfolio_id = setup_user_and_portfolio

        create_dto = CreateInvestmentDTO(
            portfolio_id=portfolio_id,
            identifier="AAPL",
            identifier_type="TICKER",
            type="stock",
        )
        created = investment_use_cases.create_investment(user_id, create_dto)

        result = investment_use_cases.get_investment(created.id, user_id)
        assert result.id == created.id
        assert result.identifier == "AAPL"

    def test_get_investment_unauthorized(
        self, investment_use_cases, setup_user_and_portfolio
    ):
        """Test getting investment owned by different user."""
        user_id, portfolio_id = setup_user_and_portfolio

        create_dto = CreateInvestmentDTO(
            portfolio_id=portfolio_id,
            identifier="AAPL",
            identifier_type="TICKER",
            type="stock",
        )
        investment = investment_use_cases.create_investment(user_id, create_dto)

        with pytest.raises(UnauthorizedException):
            investment_use_cases.get_investment(investment.id, "different-user")

    def test_list_investments_empty(
        self, investment_use_cases, setup_user_and_portfolio
    ):
        """Test listing investments when none exist."""
        user_id, portfolio_id = setup_user_and_portfolio

        result = investment_use_cases.list_investments(portfolio_id, user_id)
        assert result == []

    def test_list_investments_multiple(
        self, investment_use_cases, setup_user_and_portfolio
    ):
        """Test listing multiple investments."""
        user_id, portfolio_id = setup_user_and_portfolio

        dto1 = CreateInvestmentDTO(
            portfolio_id=portfolio_id,
            identifier="AAPL",
            identifier_type="TICKER",
            type="stock",
        )
        dto2 = CreateInvestmentDTO(
            portfolio_id=portfolio_id,
            identifier="GOOGL",
            identifier_type="TICKER",
            type="stock",
        )

        investment_use_cases.create_investment(user_id, dto1)
        investment_use_cases.create_investment(user_id, dto2)

        result = investment_use_cases.list_investments(portfolio_id, user_id)
        assert len(result) == 2

    def test_delete_investment_success(
        self, investment_use_cases, setup_user_and_portfolio
    ):
        """Test deleting an investment."""
        user_id, portfolio_id = setup_user_and_portfolio

        create_dto = CreateInvestmentDTO(
            portfolio_id=portfolio_id,
            identifier="AAPL",
            identifier_type="TICKER",
            type="stock",
        )
        investment = investment_use_cases.create_investment(user_id, create_dto)

        investment_use_cases.delete_investment(investment.id, user_id)

        with pytest.raises(EntityNotFoundException):
            investment_use_cases.get_investment(investment.id, user_id)
