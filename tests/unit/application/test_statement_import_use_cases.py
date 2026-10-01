"""Tests for the statement import use case."""

from datetime import datetime
from decimal import Decimal

import pytest

from app.application.dto.import_dto import ImportedTransactionDTO
from app.application.dto.investment_dto import CreateInvestmentDTO
from app.application.dto.user_dto import CreateUserDTO
from app.application.dto.portfolio_dto import CreatePortfolioDTO
from app.application.identifier_validation import (
    IdentifierValidator,
    ValidationResult,
)
from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.portfolio_use_cases import PortfolioUseCases
from app.application.use_cases.statement_import_use_cases import (
    StatementImportUseCases,
)
from app.application.use_cases.transaction_use_cases import TransactionUseCases
from app.application.use_cases.user_use_cases import UserUseCases
from app.domain.exceptions import UnauthorizedException
from tests.infrastructure.in_memory_repositories import (
    InMemoryInvestmentRepository,
    InMemoryPortfolioRepository,
    InMemoryTransactionRepository,
    InMemoryUserRepository,
)


def make_row(
    identifier="XS2702860896",
    title="IBRD-17NV28 3%",
    kind="buy",
    date=datetime(2025, 4, 22),
    quantity=Decimal("5000"),
    amount=Decimal("5242.45"),
    currency="EUR",
):
    return ImportedTransactionDTO(
        identifier=identifier,
        title=title,
        kind=kind,
        date=date,
        quantity=quantity,
        amount=amount,
        currency=currency,
    )


class TestStatementImportUseCases:
    """Test statement import use cases."""

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
        investment_use_cases = InvestmentUseCases(repos["investment"], repos["portfolio"])
        transaction_use_cases = TransactionUseCases(
            repos["transaction"], repos["investment"], repos["portfolio"]
        )
        return {
            "user": UserUseCases(repos["user"]),
            "portfolio": PortfolioUseCases(repos["portfolio"]),
            "import": StatementImportUseCases(
                investment_use_cases,
                transaction_use_cases,
                repos["portfolio"],
                repos["investment"],
                repos["transaction"],
            ),
        }

    @pytest.fixture
    def setup_user_and_portfolio(self, use_cases):
        user = use_cases["user"].create_user(
            CreateUserDTO(username="tester", email="t@example.com", password="secret1")
        )
        portfolio = use_cases["portfolio"].create_portfolio(
            user.id,
            CreatePortfolioDTO(user_id=user.id, name="Dossier"),
        )
        return user.id, portfolio.id

    def test_import_creates_investment_and_transactions(self, use_cases, setup_user_and_portfolio):
        user_id, portfolio_id = setup_user_and_portfolio
        rows = [
            make_row(),
            make_row(
                identifier="IE00B4L5Y983",
                title="ISHS CR WD USD-AC",
                quantity=Decimal("4"),
                amount=Decimal("431.30"),
            ),
            make_row(
                kind="coupon",
                date=datetime(2025, 8, 18),
                amount=Decimal("273.00"),
            ),
        ]

        result = use_cases["import"].import_transactions(user_id, portfolio_id, rows, "FINECO")

        assert len(result.created_investments) == 2
        assert result.created_transactions == 3
        assert result.skipped_transactions == 0

        # Asset class guessing: coupon-bearing name -> bond, ISHS -> etf.
        types = sorted((inv.identifier, inv.type) for inv in result.created_investments)
        assert types == [("IE00B4L5Y983", "etf"), ("XS2702860896", "bond")]

    def test_import_reuses_existing_investment(self, use_cases, setup_user_and_portfolio):
        user_id, portfolio_id = setup_user_and_portfolio
        result = use_cases["import"].import_transactions(
            user_id, portfolio_id, [make_row()], "FINECO"
        )
        result2 = use_cases["import"].import_transactions(
            user_id, portfolio_id, [make_row()], "FINECO"
        )

        assert len(result.created_investments) == 1
        assert result2.created_investments == []
        # The identical row is a duplicate and gets skipped.
        assert result2.skipped_transactions == 1
        assert result2.created_transactions == 0

    def test_import_skips_duplicates_only_for_matching_rows(
        self, use_cases, setup_user_and_portfolio
    ):
        user_id, portfolio_id = setup_user_and_portfolio
        rows = [make_row(), make_row(amount=Decimal("5241.95"))]
        result = use_cases["import"].import_transactions(user_id, portfolio_id, rows, "FINECO")
        # Different amounts: both are distinct buys.
        assert result.created_transactions == 2
        assert result.skipped_transactions == 0

    def test_import_rejects_other_users_portfolio(self, use_cases, setup_user_and_portfolio):
        user_id, portfolio_id = setup_user_and_portfolio
        other = use_cases["user"].create_user(
            CreateUserDTO(username="other", email="o@example.com", password="secret1")
        )
        with pytest.raises(UnauthorizedException):
            use_cases["import"].import_transactions(other.id, portfolio_id, [make_row()], "FINECO")


class StubIdentifierValidator(IdentifierValidator):
    """Canned results for import tests; records every batched call."""

    def __init__(self, results=None):
        self.results = results or {}
        self.calls = []

    def validate(self, identifier: str, identifier_type: str = "ISIN") -> ValidationResult:
        return self.validate_many([identifier], identifier_type)[
            identifier.strip().upper()
        ]

    def validate_many(
        self, identifiers, identifier_type: str = "ISIN"
    ):
        self.calls.append(list(identifiers))
        return {
            identifier: self.results.get(
                identifier, ValidationResult(is_valid=True)
            )
            for identifier in identifiers
        }


class TestStatementImportValidation:
    """Test external identifier validation in the import flow."""

    @pytest.fixture
    def repos(self):
        return {
            "user": InMemoryUserRepository(),
            "portfolio": InMemoryPortfolioRepository(),
            "investment": InMemoryInvestmentRepository(),
            "transaction": InMemoryTransactionRepository(),
        }

    def _make_use_cases(self, repos, validator=None):
        investment_use_cases = InvestmentUseCases(
            repos["investment"], repos["portfolio"]
        )
        transaction_use_cases = TransactionUseCases(
            repos["transaction"], repos["investment"], repos["portfolio"]
        )
        user_use_cases = UserUseCases(repos["user"])
        portfolio_use_cases = PortfolioUseCases(repos["portfolio"])
        statement_use_cases = StatementImportUseCases(
            investment_use_cases,
            transaction_use_cases,
            repos["portfolio"],
            repos["investment"],
            repos["transaction"],
            identifier_validator=validator,
        )
        return user_use_cases, portfolio_use_cases, statement_use_cases

    @pytest.fixture
    def setup(self, repos):
        def _setup(validator=None):
            (
                user_use_cases,
                portfolio_use_cases,
                statement_use_cases,
            ) = self._make_use_cases(repos, validator)
            user = user_use_cases.create_user(
                CreateUserDTO(
                    username="tester", email="t@example.com", password="secret1"
                )
            )
            portfolio = portfolio_use_cases.create_portfolio(
                user.id, CreatePortfolioDTO(user_id=user.id, name="Dossier")
            )
            return statement_use_cases, user.id, portfolio.id

        return _setup

    def test_invalid_isin_skips_row_and_reports_it(self, setup):
        validator = StubIdentifierValidator(
            results={
                "IT0005322855": ValidationResult(
                    is_valid=False, message="Invalid idValue format."
                )
            }
        )
        use_cases, user_id, portfolio_id = setup(validator)
        rows = [
            make_row(identifier="IT0005322855", title="TYPPO BOND 3%"),
            make_row(identifier="XS2702860896", title="IBRD-17NV28 3%"),
        ]

        result = use_cases.import_transactions(user_id, portfolio_id, rows, "FINECO")

        assert result.created_transactions == 1
        assert len(result.created_investments) == 1
        assert result.created_investments[0].identifier == "XS2702860896"
        assert len(result.invalid_identifiers) == 1
        invalid = result.invalid_identifiers[0]
        assert invalid.identifier == "IT0005322855"
        assert invalid.title == "TYPPO BOND 3%"
        assert "Invalid idValue format." in invalid.reason

    def test_name_taken_from_title(self, setup):
        use_cases, user_id, portfolio_id = setup(StubIdentifierValidator())

        result = use_cases.import_transactions(
            user_id, portfolio_id, [make_row()], "FINECO"
        )

        assert result.created_investments[0].name == "IBRD-17NV28 3%"

    def test_name_falls_back_to_validator_when_title_is_isin(self, setup):
        validator = StubIdentifierValidator(
            results={
                "IT0005518128": ValidationResult(
                    is_valid=True, name="BUONI POLIENNALI DEL TES"
                )
            }
        )
        use_cases, user_id, portfolio_id = setup(validator)
        row = make_row(identifier="IT0005518128", title="IT0005518128")

        result = use_cases.import_transactions(user_id, portfolio_id, [row], "FINECO")

        assert result.created_investments[0].name == "BUONI POLIENNALI DEL TES"

    def test_validator_type_overrides_title_guess(self, setup):
        validator = StubIdentifierValidator(
            results={
                "XS2702860896": ValidationResult(
                    is_valid=True, security_type="bond"
                )
            }
        )
        use_cases, user_id, portfolio_id = setup(validator)
        # No coupon pattern in the title, so the guess alone would say "other".
        row = make_row(identifier="XS2702860896", title="IBRD NOTE")

        result = use_cases.import_transactions(user_id, portfolio_id, [row], "FINECO")

        assert result.created_investments[0].type == "bond"

    def test_without_validator_bad_checksum_skips_row(self, setup):
        # No validator wired: the domain check-digit rejection is the only guard.
        use_cases, user_id, portfolio_id = setup(None)
        rows = [
            make_row(identifier="IT0005322855", title="TYPPO BOND 3%"),
            make_row(identifier="XS2702860896", title="IBRD-17NV28 3%"),
        ]

        result = use_cases.import_transactions(user_id, portfolio_id, rows, "FINECO")

        # The bad row is reported, the good row still imports, and no
        # exception escapes the loop.
        assert len(result.invalid_identifiers) == 1
        assert result.invalid_identifiers[0].identifier == "IT0005322855"
        assert result.created_transactions == 1

    def test_lowercase_isin_does_not_duplicate_investment(self, setup):
        use_cases, user_id, portfolio_id = setup(StubIdentifierValidator())
        first = use_cases.import_transactions(
            user_id, portfolio_id, [make_row(identifier="XS2702860896")], "FINECO"
        )
        second = use_cases.import_transactions(
            user_id, portfolio_id, [make_row(identifier="xs2702860896")], "FINECO"
        )

        assert len(first.created_investments) == 1
        assert second.created_investments == []
        assert second.skipped_transactions == 1

    def test_validator_receives_only_new_identifiers(self, repos):
        user_use_cases = UserUseCases(repos["user"])
        portfolio_use_cases = PortfolioUseCases(repos["portfolio"])
        investment_use_cases = InvestmentUseCases(
            repos["investment"], repos["portfolio"]
        )
        transaction_use_cases = TransactionUseCases(
            repos["transaction"], repos["investment"], repos["portfolio"]
        )
        user = user_use_cases.create_user(
            CreateUserDTO(
                username="tester", email="t@example.com", password="secret1"
            )
        )
        portfolio = portfolio_use_cases.create_portfolio(
            user.id, CreatePortfolioDTO(user_id=user.id, name="Dossier")
        )

        # Pre-seed the investment so the import has nothing new to validate.
        investment_use_cases.create_investment(
            user.id,
            CreateInvestmentDTO(
                portfolio_id=portfolio.id,
                identifier="XS2702860896",
                identifier_type="ISIN",
                type="bond",
            ),
        )

        validator = StubIdentifierValidator()
        statement_use_cases = StatementImportUseCases(
            investment_use_cases,
            transaction_use_cases,
            repos["portfolio"],
            repos["investment"],
            repos["transaction"],
            identifier_validator=validator,
        )

        statement_use_cases.import_transactions(
            user.id, portfolio.id, [make_row()], "FINECO"
        )

        assert validator.calls == []

    def test_validator_batched_single_call(self, setup):
        validator = StubIdentifierValidator()
        use_cases, user_id, portfolio_id = setup(validator)
        rows = [
            make_row(identifier="XS2702860896", title="A 3%"),
            make_row(identifier="XS2702860896", title="A 3%", amount=Decimal("1")),
            make_row(identifier="IE00B4L5Y983", title="ISHS ETF"),
            make_row(
                identifier="IT0005518128", title="BTP 4.4%", amount=Decimal("2")
            ),
        ]

        use_cases.import_transactions(user_id, portfolio_id, rows, "FINECO")

        # One batched call with the distinct new identifiers, uppercased.
        assert len(validator.calls) == 1
        assert sorted(validator.calls[0]) == [
            "IE00B4L5Y983",
            "IT0005518128",
            "XS2702860896",
        ]
