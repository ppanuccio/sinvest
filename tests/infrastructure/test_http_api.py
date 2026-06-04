from datetime import datetime
from fastapi.testclient import TestClient

from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.portfolio_use_cases import PortfolioUseCases
from app.application.use_cases.transaction_use_cases import TransactionUseCases
from app.application.use_cases.user_use_cases import UserUseCases
from app.infrastructure import http_api
from app.infrastructure.file_based_repositories import (
    FileBasedInvestmentRepository,
    FileBasedPortfolioRepository,
    FileBasedTransactionRepository,
    FileBasedUserRepository,
)


def _create_test_client(tmp_path) -> TestClient:
    user_repo = FileBasedUserRepository(str(tmp_path / "users.json"))
    portfolio_repo = FileBasedPortfolioRepository(
        str(tmp_path / "portfolios.json")
    )
    investment_repo = FileBasedInvestmentRepository(
        str(tmp_path / "investments.json")
    )
    transaction_repo = FileBasedTransactionRepository(
        str(tmp_path / "transactions.json")
    )

    http_api.user_repository = user_repo
    http_api.portfolio_repository = portfolio_repo
    http_api.investment_repository = investment_repo
    http_api.transaction_repository = transaction_repo

    http_api.user_use_cases = UserUseCases(user_repo)
    http_api.portfolio_use_cases = PortfolioUseCases(portfolio_repo)
    http_api.investment_use_cases = InvestmentUseCases(
        investment_repo, portfolio_repo
    )
    http_api.transaction_use_cases = TransactionUseCases(
        transaction_repo, investment_repo, portfolio_repo
    )

    return TestClient(http_api.app)


def test_http_api_end_to_end_flow(tmp_path):
    client = _create_test_client(tmp_path)

    # Create a user
    response = client.post(
        "/users",
        json={
            "username": "john",
            "email": "john@example.com",
            "password": "securepass",
        },
    )
    assert response.status_code == 201
    user_data = response.json()
    assert user_data["username"] == "john"
    assert user_data["email"] == "john@example.com"
    user_id = user_data["id"]

    # Create a portfolio for the user
    response = client.post(
        f"/users/{user_id}/portfolios",
        json={"name": "Test Portfolio", "description": "Integration test"},
    )
    assert response.status_code == 201
    portfolio_data = response.json()
    assert portfolio_data["user_id"] == user_id
    assert portfolio_data["name"] == "Test Portfolio"
    portfolio_id = portfolio_data["id"]

    # List portfolios and verify the new portfolio is present
    response = client.get(f"/users/{user_id}/portfolios")
    assert response.status_code == 200
    portfolios = response.json()
    assert len(portfolios) == 1
    assert portfolios[0]["id"] == portfolio_id

    # Create an investment in the portfolio
    response = client.post(
        f"/users/{user_id}/portfolios/{portfolio_id}/investments",
        json={
            "identifier": "AAPL",
            "identifier_type": "TICKER",
            "type": "stock",
        },
    )
    assert response.status_code == 201
    investment_data = response.json()
    assert investment_data["portfolio_id"] == portfolio_id
    assert investment_data["identifier"] == "AAPL"
    investment_id = investment_data["id"]

    # List investments in the portfolio
    response = client.get(
        f"/users/{user_id}/portfolios/{portfolio_id}/investments"
    )
    assert response.status_code == 200
    investments = response.json()
    assert len(investments) == 1
    assert investments[0]["id"] == investment_id

    # Create a transaction for the investment
    response = client.post(
        f"/users/{user_id}/investments/{investment_id}/transactions",
        json={
            "amount": "150.00",
            "quantity": "10.0",
            "broker": "TestBroker",
            "date": "2024-01-01T10:00:00",
        },
    )
    assert response.status_code == 201
    transaction_data = response.json()
    assert transaction_data["investment_id"] == investment_id
    assert transaction_data["broker"] == "TestBroker"
    assert datetime.fromisoformat(transaction_data["date"]) == datetime(
        2024, 1, 1, 10, 0, 0
    )

    # List transactions for the investment
    response = client.get(
        f"/users/{user_id}/investments/{investment_id}/transactions"
    )
    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 1
    assert transactions[0]["id"] == transaction_data["id"]
