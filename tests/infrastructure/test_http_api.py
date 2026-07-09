from datetime import datetime
from fastapi.testclient import TestClient

from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.portfolio_use_cases import PortfolioUseCases
from app.application.use_cases.transaction_use_cases import TransactionUseCases
from app.application.use_cases.user_use_cases import UserUseCases
from app.application.use_cases.authentication_use_cases import AuthenticationUseCases
from app.infrastructure import http_api
from app.infrastructure.file_based_repositories import (
    FileBasedCredentialRepository,
    FileBasedInvestmentRepository,
    FileBasedPortfolioRepository,
    FileBasedTransactionRepository,
    FileBasedUserRepository,
)
from app.infrastructure.security import HMACTokenService, PBKDF2PasswordHasher


def _create_test_client(tmp_path) -> TestClient:
    user_repo = FileBasedUserRepository(str(tmp_path / "users.json"))
    credential_repo = FileBasedCredentialRepository(
        str(tmp_path / "credentials.json")
    )
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
    http_api.credential_repository = credential_repo
    http_api.portfolio_repository = portfolio_repo
    http_api.investment_repository = investment_repo
    http_api.transaction_repository = transaction_repo

    http_api.user_use_cases = UserUseCases(user_repo)
    http_api.password_hasher = PBKDF2PasswordHasher(iterations=1_000)
    http_api.token_service = HMACTokenService(secret="test-secret")
    http_api.authentication_use_cases = AuthenticationUseCases(
        http_api.user_use_cases,
        user_repo,
        credential_repo,
        http_api.password_hasher,
        http_api.token_service,
    )
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

    # Protected routes require a bearer token
    response = client.get(f"/users/{user_id}/portfolios")
    assert response.status_code == 401

    # Login and use the issued bearer token
    response = client.post(
        "/auth/login",
        json={"username": "john", "password": "securepass"},
    )
    assert response.status_code == 200
    token_data = response.json()
    assert token_data["token_type"] == "bearer"
    assert token_data["user_id"] == user_id
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    response = client.post(
        "/users",
        json={
            "username": "jane",
            "email": "jane@example.com",
            "password": "securepass",
        },
    )
    assert response.status_code == 201
    other_user_id = response.json()["id"]

    response = client.get(
        f"/users/{other_user_id}/portfolios",
        headers=headers,
    )
    assert response.status_code == 403

    # Create a portfolio for the user
    response = client.post(
        f"/users/{user_id}/portfolios",
        json={"name": "Test Portfolio", "description": "Integration test"},
        headers=headers,
    )
    assert response.status_code == 201
    portfolio_data = response.json()
    assert portfolio_data["user_id"] == user_id
    assert portfolio_data["name"] == "Test Portfolio"
    portfolio_id = portfolio_data["id"]

    # List portfolios and verify the new portfolio is present
    response = client.get(f"/users/{user_id}/portfolios", headers=headers)
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
        headers=headers,
    )
    assert response.status_code == 201
    investment_data = response.json()
    assert investment_data["portfolio_id"] == portfolio_id
    assert investment_data["identifier"] == "AAPL"
    investment_id = investment_data["id"]

    # List investments in the portfolio
    response = client.get(
        f"/users/{user_id}/portfolios/{portfolio_id}/investments",
        headers=headers,
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
        headers=headers,
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
        f"/users/{user_id}/investments/{investment_id}/transactions",
        headers=headers,
    )
    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 1
    assert transactions[0]["id"] == transaction_data["id"]
