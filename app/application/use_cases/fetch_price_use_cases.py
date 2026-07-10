"""Fetch Price use cases - orchestrates fetching current prices from external APIs."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.domain.entities.price_history import PriceHistory
from app.domain.repositories.price_history_repository import PriceHistoryRepository
from app.domain.repositories.investment_repository import InvestmentRepository
from app.domain.repositories.portfolio_repository import PortfolioRepository
from app.domain.value_objects import Money
from app.domain.exceptions import (
    EntityNotFoundException,
    UnauthorizedException,
)
from app.application.dto.price_history_dto import PriceHistoryResponseDTO
from app.infrastructure.external.yahoo_finance_price_service import (
    YahooFinancePriceService,
    YahooFinanceError,
)


class FetchPriceUseCases:
    """Orchestrates fetching and storing current prices from external APIs."""

    def __init__(
        self,
        price_history_repository: PriceHistoryRepository,
        investment_repository: InvestmentRepository,
        portfolio_repository: PortfolioRepository,
    ):
        self.price_history_repository = price_history_repository
        self.investment_repository = investment_repository
        self.portfolio_repository = portfolio_repository

    async def fetch_and_store_current_price(
        self, user_id: str, investment_id: str
    ) -> PriceHistoryResponseDTO:
        """
        Fetch current price from Yahoo Finance and store it.

        Args:
            user_id: ID of the user (for authorization)
            investment_id: ID of the investment to fetch price for

        Returns:
            PriceHistoryResponseDTO with the stored price

        Raises:
            EntityNotFoundException: If investment not found
            UnauthorizedException: If user doesn't own the investment
            YahooFinanceError: If Yahoo Finance API fails
        """
        # Verify investment exists and belongs to user
        investment = self.investment_repository.get_by_id(investment_id)
        if not investment:
            raise EntityNotFoundException("Investment", investment_id)

        portfolio = self.portfolio_repository.get_by_id(investment.portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own investment {investment_id}"
            )

        # Get symbol from investment identifier
        symbol = investment.identifier.value

        # Fetch price from Yahoo Finance
        async with YahooFinancePriceService() as price_service:
            try:
                quote = await price_service.fetch_price(symbol)
            except YahooFinanceError as e:
                hint = ""
                if "." not in symbol and not symbol.startswith("^"):
                    hint = " For European ETFs/stocks, try adding an exchange suffix (.DE, .MI, .AS, .L, .PA, .SW)."
                raise YahooFinanceError(f"Failed to fetch price for {symbol}: {e}{hint}")

        # Create price history entity
        price_history = PriceHistory(
            id=str(uuid.uuid4()),
            investment_id=investment_id,
            price=Money(quote.price, quote.currency),
            date=datetime.utcfromtimestamp(quote.timestamp),
            created_at=datetime.utcnow(),
        )

        # Save and return
        saved = self.price_history_repository.save(price_history)
        return self._to_response_dto(saved)

    async def fetch_and_store_multiple_prices(
        self, user_id: str, investment_ids: list[str]
    ) -> list[PriceHistoryResponseDTO]:
        """
        Fetch and store current prices for multiple investments.

        Args:
            user_id: ID of the user (for authorization)
            investment_ids: List of investment IDs to fetch prices for

        Returns:
            List of PriceHistoryResponseDTO for successfully fetched prices
        """
        results = []
        symbols = []

        # First, verify all investments and collect symbols
        for investment_id in investment_ids:
            investment = self.investment_repository.get_by_id(investment_id)
            if not investment:
                # Skip invalid investments
                continue
            portfolio = self.portfolio_repository.get_by_id(investment.portfolio_id)
            if not portfolio or portfolio.user_id != user_id:
                # Skip unauthorized investments
                continue
            symbols.append((investment_id, investment.identifier.value))

        if not symbols:
            return []

        # Fetch prices in batch
        symbol_list = [s[1] for s in symbols]
        async with YahooFinancePriceService() as price_service:
            try:
                quotes = await price_service.fetch_prices(symbol_list)
            except YahooFinanceError as e:
                raise YahooFinanceError(f"Failed to fetch prices: {e}")

        # Match quotes to investments and store
        for quote in quotes:
            # Find the investment_id for this symbol
            matching = [s for s in symbols if s[1] == quote.symbol]
            if not matching:
                continue
            investment_id = matching[0][0]

            price_history = PriceHistory(
                id=str(uuid.uuid4()),
                investment_id=investment_id,
                price=Money(quote.price, quote.currency),
                date=datetime.utcfromtimestamp(quote.timestamp),
                created_at=datetime.utcnow(),
            )
            saved = self.price_history_repository.save(price_history)
            results.append(self._to_response_dto(saved))

        return results

    def _to_response_dto(
        self, price_history: PriceHistory
    ) -> PriceHistoryResponseDTO:
        """Convert price history entity to response DTO."""
        return PriceHistoryResponseDTO(
            id=price_history.id,
            investment_id=price_history.investment_id,
            price=price_history.price.amount,
            date=price_history.date,
            created_at=price_history.created_at,
        )