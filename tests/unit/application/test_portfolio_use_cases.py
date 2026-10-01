"""Tests for portfolio use cases."""

import pytest
from datetime import datetime
from decimal import Decimal

from app.application.use_cases.portfolio_use_cases import PortfolioUseCases
from app.application.use_cases.user_use_cases import UserUseCases
from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.transaction_use_cases import TransactionUseCases
from app.application.dto.portfolio_dto import (
    CreatePortfolioDTO,
    UpdatePortfolioDTO,
)
from app.application.dto.investment_dto import CreateInvestmentDTO
from app.application.dto.transaction_dto import CreateTransactionDTO
from app.application.dto.user_dto import CreateUserDTO
from app.domain.exceptions import (
    EntityNotFoundException,
    UnauthorizedException,
)
from tests.infrastructure.in_memory_repositories import (
    InMemoryPortfolioRepository,
    InMemoryUserRepository,
    InMemoryInvestmentRepository,
    InMemoryTransactionRepository,
    InMemoryPriceHistoryRepository,
)


class TestPortfolioUseCases:
    """Test portfolio use cases."""

    @pytest.fixture
    def user_repo(self):
        return InMemoryUserRepository()

    @pytest.fixture
    def portfolio_repo(self):
        return InMemoryPortfolioRepository()

    @pytest.fixture
    def user_use_cases(self, user_repo):
        return UserUseCases(user_repo)

    @pytest.fixture
    def portfolio_use_cases(self, portfolio_repo):
        return PortfolioUseCases(portfolio_repo)

    @pytest.fixture
    def user_id(self, user_use_cases):
        """Create a test user and return ID."""
        dto = CreateUserDTO(
            username="test_user",
            email="test@example.com",
            password="password123",
        )
        user = user_use_cases.create_user(dto)
        return user.id

    def test_create_portfolio_success(self, portfolio_use_cases, user_id):
        """Test creating a portfolio."""
        dto = CreatePortfolioDTO(
            user_id=user_id,
            name="My Portfolio",
            description="Test portfolio",
        )
        result = portfolio_use_cases.create_portfolio(user_id, dto)

        assert result.id is not None
        assert result.user_id == user_id
        assert result.name == "My Portfolio"
        assert result.description == "Test portfolio"

    def test_create_portfolio_different_user_fails(self, portfolio_use_cases, user_id):
        """Test that creating portfolio for different user fails."""
        dto = CreatePortfolioDTO(
            user_id="different-user-id",
            name="My Portfolio",
            description="Test portfolio",
        )
        with pytest.raises(UnauthorizedException):
            portfolio_use_cases.create_portfolio(user_id, dto)

    def test_create_portfolio_invalid_name(self, portfolio_use_cases, user_id):
        """Test that short name fails."""
        dto = CreatePortfolioDTO(
            user_id=user_id,
            name="X",  # Too short
            description="Test",
        )
        with pytest.raises(ValueError):
            portfolio_use_cases.create_portfolio(user_id, dto)

    def test_get_portfolio_success(self, portfolio_use_cases, user_id):
        """Test retrieving a portfolio."""
        create_dto = CreatePortfolioDTO(
            user_id=user_id,
            name="My Portfolio",
        )
        created = portfolio_use_cases.create_portfolio(user_id, create_dto)

        result = portfolio_use_cases.get_portfolio(created.id, user_id)
        assert result.id == created.id
        assert result.name == "My Portfolio"

    def test_get_portfolio_not_found(self, portfolio_use_cases, user_id):
        """Test getting non-existent portfolio."""
        with pytest.raises(EntityNotFoundException):
            portfolio_use_cases.get_portfolio("non-existent", user_id)

    def test_get_portfolio_unauthorized(self, portfolio_use_cases, user_id):
        """Test getting portfolio owned by different user."""
        create_dto = CreatePortfolioDTO(
            user_id=user_id,
            name="My Portfolio",
        )
        portfolio = portfolio_use_cases.create_portfolio(user_id, create_dto)

        with pytest.raises(UnauthorizedException):
            portfolio_use_cases.get_portfolio(portfolio.id, "different-user")

    def test_list_portfolios_empty(self, portfolio_use_cases, user_id):
        """Test listing portfolios when none exist."""
        result = portfolio_use_cases.list_portfolios(user_id)
        assert result == []

    def test_list_portfolios_multiple(self, portfolio_use_cases, user_id):
        """Test listing multiple portfolios."""
        dto1 = CreatePortfolioDTO(user_id=user_id, name="Portfolio 1")
        dto2 = CreatePortfolioDTO(user_id=user_id, name="Portfolio 2")

        portfolio_use_cases.create_portfolio(user_id, dto1)
        portfolio_use_cases.create_portfolio(user_id, dto2)

        result = portfolio_use_cases.list_portfolios(user_id)
        assert len(result) == 2

    def test_update_portfolio_success(self, portfolio_use_cases, user_id):
        """Test updating a portfolio."""
        create_dto = CreatePortfolioDTO(user_id=user_id, name="Old Name")
        portfolio = portfolio_use_cases.create_portfolio(user_id, create_dto)

        update_dto = UpdatePortfolioDTO(
            name="New Name",
            description="Updated description",
        )
        result = portfolio_use_cases.update_portfolio(
            portfolio.id, user_id, update_dto
        )

        assert result.name == "New Name"
        assert result.description == "Updated description"

    def test_delete_portfolio_success(self, portfolio_use_cases, user_id):
        """Test deleting a portfolio."""
        create_dto = CreatePortfolioDTO(user_id=user_id, name="My Portfolio")
        portfolio = portfolio_use_cases.create_portfolio(user_id, create_dto)

        portfolio_use_cases.delete_portfolio(portfolio.id, user_id)

        with pytest.raises(EntityNotFoundException):
            portfolio_use_cases.get_portfolio(portfolio.id, user_id)

    def test_delete_portfolio_cascades_to_investments(self, user_id):
        """Deleting a portfolio removes its investments, transactions and prices."""
        portfolio_repo = InMemoryPortfolioRepository()
        investment_repo = InMemoryInvestmentRepository()
        transaction_repo = InMemoryTransactionRepository()
        price_repo = InMemoryPriceHistoryRepository()
        portfolio_use_cases = PortfolioUseCases(
            portfolio_repo, investment_repo, transaction_repo, price_repo
        )
        portfolio = portfolio_use_cases.create_portfolio(
            user_id, CreatePortfolioDTO(user_id=user_id, name="Doomed")
        )
        investment_use_cases = InvestmentUseCases(
            investment_repo, portfolio_repo
        )
        investment = investment_use_cases.create_investment(
            user_id,
            CreateInvestmentDTO(
                portfolio_id=portfolio.id,
                identifier="US0378331005",
                identifier_type="ISIN",
                type="stock",
            ),
        )
        transaction_use_cases = TransactionUseCases(
            transaction_repo, investment_repo, portfolio_repo
        )
        transaction_use_cases.create_transaction(
            user_id,
            CreateTransactionDTO(
                investment_id=investment.id,
                amount=Decimal("100"),
                quantity=Decimal("1"),
                broker="FINECO",
                date=datetime(2025, 4, 22),
                currency="USD",
                kind="buy",
            ),
        )

        portfolio_use_cases.delete_portfolio(portfolio.id, user_id)

        assert investment_repo.list_by_portfolio(portfolio.id) == []
        assert transaction_repo.list_by_investment(investment.id) == []
        # Prices for the investment are gone too (nothing left to delete).
        assert not price_repo.delete_by_investment(investment.id)
        with pytest.raises(EntityNotFoundException):
            portfolio_use_cases.get_portfolio(portfolio.id, user_id)
