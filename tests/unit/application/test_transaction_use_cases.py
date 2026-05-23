"""Tests for transaction use cases."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.application.use_cases.transaction_use_cases import TransactionUseCases
from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.portfolio_use_cases import PortfolioUseCases
from app.application.use_cases.user_use_cases import UserUseCases
from app.application.dto.transaction_dto import (
    CreateTransactionDTO,
    UpdateTransactionDTO,
)
from app.application.dto.investment_dto import CreateInvestmentDTO
from app.application.dto.portfolio_dto import CreatePortfolioDTO
from app.application.dto.user_dto import CreateUserDTO
from app.domain.exceptions import (
    EntityNotFoundException,
    UnauthorizedException,
)
from tests.infrastructure.in_memory_repositories import (
    InMemoryTransactionRepository,
    InMemoryInvestmentRepository,
    InMemoryPortfolioRepository,
    InMemoryUserRepository,
)


class TestTransactionUseCases:
    """Test transaction use cases."""

    @pytest.fixture
    def repos(self):
        return {
            "user": InMemoryUserRepository(),
            "portfolio": InMemoryPortfolioRepository(),
            "investment": InMemoryInvestmentRepository(),
            "transaction": InMemoryTransactionRepository(),
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
        }

    @pytest.fixture
    def setup_user_portfolio_investment(self, use_cases):
        """Create user, portfolio, and investment for testing."""
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

    def test_create_transaction_success(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test creating a transaction."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        dto = CreateTransactionDTO(
            investment_id=investment_id,
            amount=Decimal("1000"),
            quantity=Decimal("10"),
            broker="Interactive Brokers",
            date=datetime.utcnow() - timedelta(days=1),
        )
        result = use_cases["transaction"].create_transaction(user_id, dto)

        assert result.id is not None
        assert result.amount == Decimal("1000")
        assert result.quantity == Decimal("10")
        assert result.broker == "Interactive Brokers"

    def test_create_transaction_invalid_amount(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test that negative amount fails."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        dto = CreateTransactionDTO(
            investment_id=investment_id,
            amount=Decimal("-1000"),
            quantity=Decimal("10"),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
        )
        with pytest.raises(Exception):  # InvalidTransactionException
            use_cases["transaction"].create_transaction(user_id, dto)

    def test_create_transaction_future_date_fails(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test that future transaction date fails."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        dto = CreateTransactionDTO(
            investment_id=investment_id,
            amount=Decimal("1000"),
            quantity=Decimal("10"),
            broker="Broker",
            date=datetime.utcnow() + timedelta(days=1),
        )
        with pytest.raises(Exception):  # InvalidTransactionException
            use_cases["transaction"].create_transaction(user_id, dto)

    def test_get_transaction_success(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test retrieving a transaction."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        create_dto = CreateTransactionDTO(
            investment_id=investment_id,
            amount=Decimal("1000"),
            quantity=Decimal("10"),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
        )
        created = use_cases["transaction"].create_transaction(user_id, create_dto)

        result = use_cases["transaction"].get_transaction(created.id, user_id)
        assert result.id == created.id
        assert result.amount == Decimal("1000")

    def test_list_transactions_empty(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test listing transactions when none exist."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        result = use_cases["transaction"].list_transactions(
            investment_id, user_id
        )
        assert result == []

    def test_list_transactions_multiple(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test listing multiple transactions."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        dto1 = CreateTransactionDTO(
            investment_id=investment_id,
            amount=Decimal("1000"),
            quantity=Decimal("10"),
            broker="Broker1",
            date=datetime.utcnow() - timedelta(days=2),
        )
        dto2 = CreateTransactionDTO(
            investment_id=investment_id,
            amount=Decimal("500"),
            quantity=Decimal("5"),
            broker="Broker2",
            date=datetime.utcnow() - timedelta(days=1),
        )

        use_cases["transaction"].create_transaction(user_id, dto1)
        use_cases["transaction"].create_transaction(user_id, dto2)

        result = use_cases["transaction"].list_transactions(
            investment_id, user_id
        )
        assert len(result) == 2

    def test_delete_transaction_success(
        self, use_cases, setup_user_portfolio_investment
    ):
        """Test deleting a transaction."""
        user_id, portfolio_id, investment_id = setup_user_portfolio_investment

        create_dto = CreateTransactionDTO(
            investment_id=investment_id,
            amount=Decimal("1000"),
            quantity=Decimal("10"),
            broker="Broker",
            date=datetime.utcnow() - timedelta(days=1),
        )
        transaction = use_cases["transaction"].create_transaction(
            user_id, create_dto
        )

        use_cases["transaction"].delete_transaction(transaction.id, user_id)

        with pytest.raises(EntityNotFoundException):
            use_cases["transaction"].get_transaction(transaction.id, user_id)
