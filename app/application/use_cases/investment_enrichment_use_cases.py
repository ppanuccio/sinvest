"""Investment enrichment use cases - backfill security names from reference data."""

import asyncio
from dataclasses import dataclass
from typing import List

import yfinance as yf

from app.application.identifier_validation import IdentifierValidator
from app.domain.entities.investment import Investment
from app.domain.exceptions import EntityNotFoundException, UnauthorizedException
from app.domain.repositories.investment_repository import InvestmentRepository
from app.domain.repositories.portfolio_repository import PortfolioRepository


@dataclass
class NameEnrichmentResultDTO:
    """Outcome of a name-enrichment pass over a portfolio."""

    enriched: List[Investment]  # investments whose name was just set
    already_named: int  # investments that already had a name
    unresolved: List[str]  # identifiers where no name could be found


class InvestmentEnrichmentUseCases:
    """Fill in missing security names on existing investments.

    ISINs are resolved through the external identifier validator (OpenFIGI,
    one batched request); tickers through Yahoo Finance. Investments that
    already carry a name are left untouched, so re-running is harmless.
    """

    def __init__(
        self,
        investment_repository: InvestmentRepository,
        portfolio_repository: PortfolioRepository,
        identifier_validator: IdentifierValidator,
    ):
        self.investment_repository = investment_repository
        self.portfolio_repository = portfolio_repository
        self.identifier_validator = identifier_validator

    async def enrich_portfolio_names(
        self, user_id: str, portfolio_id: str
    ) -> NameEnrichmentResultDTO:
        """Set the name on every nameless investment in the portfolio."""
        portfolio = self.portfolio_repository.get_by_id(portfolio_id)
        if not portfolio:
            raise EntityNotFoundException("Portfolio", portfolio_id)
        if portfolio.user_id != user_id:
            raise UnauthorizedException(f"User {user_id} does not own portfolio {portfolio_id}")

        investments = self.investment_repository.list_by_portfolio(portfolio_id)
        already_named = sum(1 for inv in investments if inv.name)
        nameless = [inv for inv in investments if not inv.name]

        # ISINs in one batched external call; tickers resolved via Yahoo.
        isin_keys = [
            inv.identifier.value for inv in nameless if inv.identifier.identifier_type == "ISIN"
        ]
        validation = self.identifier_validator.validate_many(isin_keys, "ISIN") if isin_keys else {}

        enriched: List[Investment] = []
        unresolved: List[str] = []
        for inv in nameless:
            name = await self._resolve_name(inv, validation)
            if not name:
                unresolved.append(inv.identifier.value)
                continue
            inv.update_details(name=name)
            self.investment_repository.update(inv)
            enriched.append(inv)

        return NameEnrichmentResultDTO(
            enriched=enriched,
            already_named=already_named,
            unresolved=unresolved,
        )

    async def _resolve_name(self, investment: Investment, validation: dict) -> str | None:
        if investment.identifier.identifier_type == "ISIN":
            outcome = validation.get(investment.identifier.value)
            return outcome.name if outcome else None
        return await self._yahoo_name(investment.identifier.value)

    @staticmethod
    async def _yahoo_name(symbol: str) -> str | None:
        """Look up a ticker's name from Yahoo Finance; None on any failure."""
        try:
            ticker = await asyncio.to_thread(yf.Ticker, symbol)
            info = await asyncio.to_thread(lambda: ticker.info)
            return info.get("shortName") or info.get("longName") or None
        except Exception:
            return None
