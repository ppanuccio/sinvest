"""Tests for the investment name-enrichment use case."""

import pytest

from app.application.dto.investment_dto import CreateInvestmentDTO
from app.application.dto.portfolio_dto import CreatePortfolioDTO
from app.application.dto.user_dto import CreateUserDTO
from app.application.identifier_validation import (
    IdentifierValidator,
    ValidationResult,
)
from app.application.use_cases.investment_enrichment_use_cases import (
    InvestmentEnrichmentUseCases,
)
from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.portfolio_use_cases import PortfolioUseCases
from app.application.use_cases.user_use_cases import UserUseCases
from app.domain.exceptions import UnauthorizedException
from tests.infrastructure.in_memory_repositories import (
    InMemoryInvestmentRepository,
    InMemoryPortfolioRepository,
    InMemoryUserRepository,
)


class StubIdentifierValidator(IdentifierValidator):
    def __init__(self, results=None):
        self.results = results or {}

    def validate(self, identifier: str, identifier_type: str = "ISIN") -> ValidationResult:
        return self.validate_many([identifier], identifier_type)[identifier.strip().upper()]

    def validate_many(self, identifiers, identifier_type: str = "ISIN"):
        return {
            identifier: self.results.get(identifier, ValidationResult(is_valid=True))
            for identifier in identifiers
        }


@pytest.fixture
def yahoo_names(monkeypatch):
    """Replace the Yahoo lookup with canned answers; returns the dict."""
    canned = {}

    async def fake_yahoo(symbol):
        return canned.get(symbol)

    monkeypatch.setattr(InvestmentEnrichmentUseCases, "_yahoo_name", staticmethod(fake_yahoo))
    return canned


class TestInvestmentEnrichmentUseCases:
    @pytest.fixture
    def repos(self):
        return {
            "user": InMemoryUserRepository(),
            "portfolio": InMemoryPortfolioRepository(),
            "investment": InMemoryInvestmentRepository(),
        }

    @pytest.fixture
    def setup(self, repos):
        def _setup(validator):
            user = UserUseCases(repos["user"]).create_user(
                CreateUserDTO(username="tester", email="t@example.com", password="secret1")
            )
            portfolio = PortfolioUseCases(repos["portfolio"]).create_portfolio(
                user.id, CreatePortfolioDTO(user_id=user.id, name="Dossier")
            )
            investment_use_cases = InvestmentUseCases(repos["investment"], repos["portfolio"])
            enrichment = InvestmentEnrichmentUseCases(
                repos["investment"], repos["portfolio"], validator
            )
            return investment_use_cases, enrichment, user.id, portfolio.id

        return _setup

    @staticmethod
    def _add_investment(
        investment_use_cases,
        user_id,
        portfolio_id,
        identifier,
        identifier_type,
        name=None,
    ):
        dto = CreateInvestmentDTO(
            portfolio_id=portfolio_id,
            identifier=identifier,
            identifier_type=identifier_type,
            type="bond" if identifier_type == "ISIN" else "etf",
        )
        created = investment_use_cases.create_investment(user_id, dto)
        if name is not None:
            entity = investment_use_cases.investment_repository.get_by_id(created.id)
            entity.update_details(name=name)
            investment_use_cases.investment_repository.update(entity)
        return created.id

    async def test_enriches_isin_and_ticker_names(self, setup, yahoo_names):
        validator = StubIdentifierValidator(
            results={
                "IT0005518128": ValidationResult(is_valid=True, name="BUONI POLIENNALI DEL TES")
            }
        )
        investment_use_cases, enrichment, user_id, portfolio_id = setup(validator)
        self._add_investment(investment_use_cases, user_id, portfolio_id, "IT0005518128", "ISIN")
        self._add_investment(investment_use_cases, user_id, portfolio_id, "VWCE.DE", "TICKER")
        # Already named — must stay untouched.
        self._add_investment(
            investment_use_cases,
            user_id,
            portfolio_id,
            "US0378331005",
            "ISIN",
            name="Apple",
        )
        yahoo_names["VWCE.DE"] = "Vanguard FTSE All-World"

        result = await enrichment.enrich_portfolio_names(user_id, portfolio_id)

        assert len(result.enriched) == 2
        assert result.already_named == 1
        assert result.unresolved == []
        names = {inv.identifier.value: inv.name for inv in result.enriched}
        assert names["IT0005518128"] == "BUONI POLIENNALI DEL TES"
        assert names["VWCE.DE"] == "Vanguard FTSE All-World"

    async def test_unresolved_identifiers_reported(self, setup, yahoo_names):
        validator = StubIdentifierValidator()  # no names for anyone
        investment_use_cases, enrichment, user_id, portfolio_id = setup(validator)
        self._add_investment(investment_use_cases, user_id, portfolio_id, "IT0005532715", "ISIN")
        self._add_investment(investment_use_cases, user_id, portfolio_id, "XX.BO", "TICKER")

        result = await enrichment.enrich_portfolio_names(user_id, portfolio_id)

        assert result.enriched == []
        assert sorted(result.unresolved) == ["IT0005532715", "XX.BO"]

    async def test_rejects_other_users_portfolio(self, repos, setup, yahoo_names):
        validator = StubIdentifierValidator()
        investment_use_cases, enrichment, user_id, portfolio_id = setup(validator)
        other = UserUseCases(repos["user"]).create_user(
            CreateUserDTO(username="other", email="o@example.com", password="secret1")
        )
        with pytest.raises(UnauthorizedException):
            await enrichment.enrich_portfolio_names(other.id, portfolio_id)
