from datetime import datetime
from fastapi.testclient import TestClient

from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.portfolio_use_cases import PortfolioUseCases
from app.application.use_cases.transaction_use_cases import TransactionUseCases
from app.application.use_cases.user_use_cases import UserUseCases
from app.application.use_cases.authentication_use_cases import AuthenticationUseCases
from app.application.use_cases.statement_import_use_cases import (
    StatementImportUseCases,
)
from app.infrastructure import http_api
from app.infrastructure.file_based_repositories import (
    FileBasedCredentialRepository,
    FileBasedInvestmentRepository,
    FileBasedPortfolioRepository,
    FileBasedTransactionRepository,
    FileBasedUserRepository,
)
from app.infrastructure.security import HMACTokenService, PBKDF2PasswordHasher
from app.application.identifier_validation import (
    IdentifierValidator,
    ValidationResult,
)
from app.application.use_cases.investment_enrichment_use_cases import (
    InvestmentEnrichmentUseCases,
)


class StubIdentifierValidator(IdentifierValidator):
    """Deterministic validator for API tests: only explicit results, no HTTP."""

    def __init__(self):
        self.results = {}
        self.calls = []

    def validate(self, identifier: str, identifier_type: str = "ISIN") -> ValidationResult:
        return self.validate_many([identifier], identifier_type)[
            identifier.strip().upper()
        ]

    def validate_many(self, identifiers, identifier_type: str = "ISIN"):
        self.calls.append(list(identifiers))
        return {
            identifier: self.results.get(
                identifier, ValidationResult(is_valid=True)
            )
            for identifier in identifiers
        }


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
    validator = StubIdentifierValidator()

    http_api.user_repository = user_repo
    http_api.credential_repository = credential_repo
    http_api.portfolio_repository = portfolio_repo
    http_api.investment_repository = investment_repo
    http_api.transaction_repository = transaction_repo
    http_api.identifier_validator = validator

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
    http_api.portfolio_use_cases = PortfolioUseCases(
        portfolio_repo, investment_repo, transaction_repo
    )
    http_api.investment_use_cases = InvestmentUseCases(
        investment_repo, portfolio_repo
    )
    http_api.transaction_use_cases = TransactionUseCases(
        transaction_repo, investment_repo, portfolio_repo
    )
    http_api.statement_import_use_cases = StatementImportUseCases(
        http_api.investment_use_cases,
        http_api.transaction_use_cases,
        portfolio_repo,
        investment_repo,
        transaction_repo,
        identifier_validator=validator,
    )
    http_api.investment_enrichment_use_cases = InvestmentEnrichmentUseCases(
        investment_repo,
        portfolio_repo,
        validator,
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


def test_import_excel_endpoint(tmp_path):
    client = _create_test_client(tmp_path)

    response = client.post(
        "/users",
        json={
            "username": "importer",
            "email": "importer@example.com",
            "password": "securepass",
        },
    )
    # Username with a leading space is still >= 3 chars, but keep it valid:
    assert response.status_code == 201
    user_id = response.json()["id"]

    response = client.post(
        "/auth/login",
        json={"username": "importer", "password": "securepass"},
    )
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    response = client.post(
        f"/users/{user_id}/portfolios",
        json={"name": "Dossier", "description": None},
        headers=headers,
    )
    assert response.status_code == 201
    portfolio_id = response.json()["id"]

    # Build a statement workbook in memory (buy + fee, coupon).
    from io import BytesIO

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(
        [
            "Operazione",
            "Data valuta",
            "Descrizione",
            "Titolo",
            "Isin",
            "Segno",
            "Quantita",
            "Divisa",
            "Prezzo",
            "Cambio",
            "Controvalore",
            None,
            None,
            None,
            "Commissioni amministrato",
        ]
    )
    ws.append(
        [
            "22/04/2025",
            "24/04/2025",
            "Compravendita titoli",
            "IBRD-17NV28 3%",
            "XS2702860896",
            "A",
            5000,
            "EUR",
            105.2191,
            1,
            5260.95,
            None,
            None,
            None,
            19,
        ]
    )
    ws.append(
        [
            "18/08/2025",
            "18/08/2025",
            "Stacco Cedole",
            "IBRD-17NV28 3%",
            "XS2702860896",
            " ",
            39000,
            "EUR",
            0,
            1,
            273,
            None,
            None,
            None,
            None,
        ]
    )
    buffer = BytesIO()
    wb.save(buffer)

    response = client.post(
        f"/users/{user_id}/portfolios/{portfolio_id}/import-excel",
        files={"file": ("statement.xlsx", buffer.getvalue())},
        data={"broker": "FINECO"},
        headers=headers,
    )
    assert response.status_code == 201
    result = response.json()
    assert result["created_transactions"] == 2
    assert len(result["created_investments"]) == 1
    assert result["created_investments"][0]["identifier"] == "XS2702860896"
    assert result["skipped_transactions"] == 0

    # Re-importing the same file creates nothing new.
    buffer2 = BytesIO(buffer.getvalue())
    response = client.post(
        f"/users/{user_id}/portfolios/{portfolio_id}/import-excel",
        files={"file": ("statement.xlsx", buffer2.getvalue())},
        data={"broker": "FINECO"},
        headers=headers,
    )
    assert response.status_code == 201
    result = response.json()
    assert result["created_transactions"] == 0
    assert result["skipped_transactions"] == 2
    assert result["created_investments"] == []

    # A non-Excel upload is a 400.
    response = client.post(
        f"/users/{user_id}/portfolios/{portfolio_id}/import-excel",
        files={"file": ("statement.xlsx", b"nope")},
        headers=headers,
    )
    assert response.status_code == 400


def test_import_excel_reports_invalid_identifiers_and_names(tmp_path):
    client = _create_test_client(tmp_path)

    response = client.post(
        "/users",
        json={
            "username": "validator",
            "email": "validator@example.com",
            "password": "securepass",
        },
    )
    user_id = response.json()["id"]
    response = client.post(
        "/auth/login",
        json={"username": "validator", "password": "securepass"},
    )
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    response = client.post(
        f"/users/{user_id}/portfolios",
        json={"name": "Dossier", "description": None},
        headers=headers,
    )
    portfolio_id = response.json()["id"]

    # The stub validator rejects one ISIN and enriches the other.
    validator = http_api.identifier_validator
    validator.results = {
        "IT0005322855": ValidationResult(
            is_valid=False, message="Invalid idValue format."
        ),
        "XS2702860896": ValidationResult(
            is_valid=True,
            name="IBRD 3.25% 17NOV2028",
            security_type="bond",
        ),
    }

    from io import BytesIO

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(
        [
            "Operazione",
            "Data valuta",
            "Descrizione",
            "Titolo",
            "Isin",
            "Segno",
            "Quantita",
            "Divisa",
            "Prezzo",
            "Cambio",
            "Controvalore",
            None,
            None,
            None,
            "Commissioni amministrato",
        ]
    )
    ws.append(
        [
            "22/04/2025",
            "24/04/2025",
            "Compravendita titoli",
            "XS2702860896",
            "XS2702860896",
            "A",
            5000,
            "EUR",
            105.2191,
            1,
            5260.95,
            None,
            None,
            None,
            19,
        ]
    )
    ws.append(
        [
            "23/04/2025",
            "24/04/2025",
            "Compravendita titoli",
            "TYPPO BOND 3%",
            "IT0005322855",
            "A",
            100,
            "EUR",
            99.0,
            1,
            9900,
            None,
            None,
            None,
            None,
        ]
    )
    buffer = BytesIO()
    wb.save(buffer)

    response = client.post(
        f"/users/{user_id}/portfolios/{portfolio_id}/import-excel",
        files={"file": ("statement.xlsx", buffer.getvalue())},
        data={"broker": "FINECO"},
        headers=headers,
    )
    assert response.status_code == 201
    result = response.json()

    # The valid row imported with the validator-enriched name; the invalid
    # one was skipped and reported.
    assert result["created_transactions"] == 1
    assert len(result["created_investments"]) == 1
    assert result["created_investments"][0]["name"] == "IBRD 3.25% 17NOV2028"
    assert len(result["invalid_identifiers"]) == 1
    invalid = result["invalid_identifiers"][0]
    assert invalid["identifier"] == "IT0005322855"
    assert invalid["title"] == "TYPPO BOND 3%"
    assert invalid["reason"] == "Invalid idValue format."


def test_delete_portfolio_cascades(tmp_path):
    client = _create_test_client(tmp_path)

    response = client.post(
        "/users",
        json={
            "username": "cascader",
            "email": "cascader@example.com",
            "password": "securepass",
        },
    )
    user_id = response.json()["id"]
    response = client.post(
        "/auth/login",
        json={"username": "cascader", "password": "securepass"},
    )
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    response = client.post(
        f"/users/{user_id}/portfolios",
        json={"name": "Doomed", "description": None},
        headers=headers,
    )
    portfolio_id = response.json()["id"]

    # A second, surviving portfolio (used for the cross-user check below).
    response = client.post(
        f"/users/{user_id}/portfolios",
        json={"name": "Survivor", "description": None},
        headers=headers,
    )
    survivor_id = response.json()["id"]

    response = client.post(
        f"/users/{user_id}/portfolios/{portfolio_id}/investments",
        json={
            "identifier": "US0378331005",
            "identifier_type": "ISIN",
            "type": "stock",
        },
        headers=headers,
    )
    assert response.status_code == 201
    investment_id = response.json()["id"]

    response = client.delete(
        f"/users/{user_id}/portfolios/{portfolio_id}", headers=headers
    )
    assert response.status_code == 204

    # Portfolio and its investment are gone.
    response = client.get(
        f"/users/{user_id}/portfolios/{portfolio_id}", headers=headers
    )
    assert response.status_code == 404
    response = client.get(
        f"/users/{user_id}/portfolios/{portfolio_id}/investments",
        headers=headers,
    )
    # The investments route 404s too: the parent portfolio no longer exists.
    assert response.status_code == 404

    # Deleting someone else's portfolio is a 403.
    response = client.post(
        "/users",
        json={
            "username": "other",
            "email": "other@example.com",
            "password": "securepass",
        },
    )
    other_id = response.json()["id"]
    response = client.post(
        "/auth/login", json={"username": "other", "password": "securepass"}
    )
    other_headers = {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }
    response = client.delete(
        f"/users/{other_id}/portfolios/{survivor_id}", headers=other_headers
    )
    assert response.status_code == 403


def test_enrich_names_endpoint(tmp_path):
    client = _create_test_client(tmp_path)

    response = client.post(
        "/users",
        json={
            "username": "naming",
            "email": "naming@example.com",
            "password": "securepass",
        },
    )
    user_id = response.json()["id"]
    response = client.post(
        "/auth/login",
        json={"username": "naming", "password": "securepass"},
    )
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    response = client.post(
        f"/users/{user_id}/portfolios",
        json={"name": "Dossier", "description": None},
        headers=headers,
    )
    portfolio_id = response.json()["id"]

    validator = http_api.identifier_validator
    validator.results = {
        "IT0005518128": ValidationResult(
            is_valid=True, name="BUONI POLIENNALI DEL TES"
        )
    }

    response = client.post(
        f"/users/{user_id}/portfolios/{portfolio_id}/investments",
        json={
            "identifier": "IT0005518128",
            "identifier_type": "ISIN",
            "type": "bond",
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["name"] is None

    # Ticker resolution goes through Yahoo; neutralize it for the test.
    import app.application.use_cases.investment_enrichment_use_cases as module

    async def fake_yahoo(symbol):
        return "Vanguard FTSE All-World"

    original = module.InvestmentEnrichmentUseCases._yahoo_name
    module.InvestmentEnrichmentUseCases._yahoo_name = staticmethod(fake_yahoo)
    try:
        response = client.post(
            f"/users/{user_id}/portfolios/{portfolio_id}/enrich-names",
            headers=headers,
        )
    finally:
        module.InvestmentEnrichmentUseCases._yahoo_name = original

    assert response.status_code == 200
    result = response.json()
    assert len(result["enriched"]) == 1
    assert result["enriched"][0]["name"] == "BUONI POLIENNALI DEL TES"
    assert result["unresolved"] == []

    # Re-running is a no-op for named investments.
    response = client.post(
        f"/users/{user_id}/portfolios/{portfolio_id}/enrich-names",
        headers=headers,
    )
    result = response.json()
    assert result["enriched"] == []
    assert result["already_named"] == 1
