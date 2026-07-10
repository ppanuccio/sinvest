"""Portfolio Analytics use cases - aggregated portfolio metrics and analysis."""

from decimal import Decimal
from datetime import datetime
from typing import List

from app.domain.repositories.portfolio_repository import PortfolioRepository
from app.domain.repositories.investment_repository import InvestmentRepository
from app.domain.repositories.transaction_repository import TransactionRepository
from app.domain.repositories.price_history_repository import (
    PriceHistoryRepository,
)
from app.domain.services.investment_calculation_service import (
    InvestmentCalculationService,
)
from app.domain.services.portfolio_calculation_service import (
    PortfolioCalculationService,
)
from app.domain.exceptions import (
    EntityNotFoundException,
    UnauthorizedException,
)
from app.application.dto.analytics_dto import (
    PortfolioAnalyticsDTO,
    InvestmentAnalyticsDTO,
)
from app.infrastructure.external.yahoo_finance_price_service import (
    YahooFinancePriceService,
    YahooFinanceError,
)


class PortfolioAnalyticsUseCases:
    """Orchestrates portfolio analytics and reporting."""

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        investment_repository: InvestmentRepository,
        transaction_repository: TransactionRepository,
        price_history_repository: PriceHistoryRepository,
    ):
        self.portfolio_repository = portfolio_repository
        self.investment_repository = investment_repository
        self.transaction_repository = transaction_repository
        self.price_history_repository = price_history_repository

    async def _fetch_rates(
        self, currencies: set[str], reference_currency: str
    ) -> dict[str, Decimal]:
        """Fetch exchange rates for all currencies to the reference currency."""
        rates: dict[str, Decimal] = {}
        to_fetch = {c for c in currencies if c != reference_currency}
        if not to_fetch:
            return rates

        async with YahooFinancePriceService() as svc:
            for currency in to_fetch:
                try:
                    rate = await svc.get_exchange_rate(currency, reference_currency)
                    rates[currency] = rate
                except YahooFinanceError:
                    pass
        return rates

    async def get_portfolio_analytics(
        self, portfolio_id: str, user_id: str, reference_currency: str = "USD"
    ) -> PortfolioAnalyticsDTO:
        """
        Calculate complete analytics for a portfolio.
        All monetary values are converted to reference_currency.

        Args:
            portfolio_id: ID of the portfolio
            user_id: ID of the owning user (for authorization)
            reference_currency: Target currency for all monetary values (default "USD")

        Returns:
            PortfolioAnalyticsDTO with all values in reference_currency
        """
        # Verify portfolio exists and belongs to user
        portfolio = self.portfolio_repository.get_by_id(portfolio_id)
        if not portfolio:
            raise EntityNotFoundException("Portfolio", portfolio_id)

        if portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own portfolio {portfolio_id}"
            )

        # Get all investments in portfolio
        investments = self.investment_repository.list_by_portfolio(
            portfolio_id
        )

        # Build data maps for calculations
        transactions_by_investment = {}
        price_history_by_investment = {}

        # Collect all currencies for exchange rate fetching
        all_currencies: set[str] = set()

        for investment in investments:
            transactions = self.transaction_repository.list_by_investment(
                investment.id
            )
            prices = self.price_history_repository.list_by_investment(
                investment.id
            )

            transactions_by_investment[investment.id] = transactions
            price_history_by_investment[investment.id] = prices

            # Collect currencies from transactions and prices
            for tx in transactions:
                all_currencies.add(tx.amount.currency)
            if prices:
                all_currencies.add(prices[0].price.currency)

        # Fetch exchange rates for all currencies to the reference currency
        rates = await self._fetch_rates(all_currencies, reference_currency)

        # Calculate portfolio totals
        (
            total_value,
            total_invested,
            total_yield,
            total_yield_pct,
        ) = PortfolioCalculationService.calculate_portfolio_totals(
            investments,
            transactions_by_investment,
            price_history_by_investment,
            reference_currency,
            rates,
        )

        # Calculate allocation percentages
        allocation = PortfolioCalculationService.calculate_allocation_percentages(
            investments,
            transactions_by_investment,
            price_history_by_investment,
            reference_currency,
            rates,
        )

        # Build investment analytics
        investment_analytics_list = []

        for investment in investments:
            transactions = transactions_by_investment.get(investment.id, [])
            prices = price_history_by_investment.get(investment.id, [])

            # Get current price and convert to reference currency
            current_price = None
            if prices:
                raw_price = prices[0].price
                if raw_price.currency == reference_currency:
                    current_price = raw_price.amount
                else:
                    rate = rates.get(raw_price.currency)
                    if rate:
                        converted = raw_price.convert_to(reference_currency, rate)
                        current_price = converted.amount
                    else:
                        current_price = raw_price.amount

            # Calculate quantity (safe — no currency dependency)
            total_qty = InvestmentCalculationService.calculate_total_quantity(
                transactions
            )

            # Calculate remaining metrics with currency conversion
            try:
                total_invested_inv = (
                    InvestmentCalculationService.calculate_total_invested_amount(
                        transactions, reference_currency, rates
                    )
                    if transactions
                    else None
                )
                initial_amount = (
                    InvestmentCalculationService.calculate_initial_amount(
                        transactions
                    )
                    if transactions
                    else None
                )

                # Calculate total value
                if prices and transactions:
                    inv_total_value = InvestmentCalculationService.calculate_total_value(
                        transactions, prices[0].price, reference_currency, rates
                    )
                    inv_yield = InvestmentCalculationService.calculate_yield(
                        inv_total_value, initial_amount
                    )
                    inv_yield_pct = InvestmentCalculationService.calculate_yield_percentage(
                        inv_yield, initial_amount
                    )
                else:
                    inv_total_value = total_invested_inv or None
                    inv_yield = None
                    inv_yield_pct = None
            except Exception:
                inv_total_value = None
                inv_yield = None
                inv_yield_pct = None

            inv_analytics = InvestmentAnalyticsDTO(
                investment_id=investment.id,
                identifier=investment.identifier.value,
                type=investment.type.value,
                total_quantity=total_qty,
                total_invested=total_invested_inv.amount if total_invested_inv else None,
                current_price=current_price,
                total_value=inv_total_value.amount if inv_total_value else None,
                initial_value=initial_amount.amount if initial_amount else None,
                yield_amount=inv_yield.amount if inv_yield else None,
                yield_percentage=inv_yield_pct,
                allocation_percentage=allocation.get(investment.id, 0),
            )
            investment_analytics_list.append(inv_analytics)

        # Build response DTO
        return PortfolioAnalyticsDTO(
            portfolio_id=portfolio_id,
            total_value=total_value.amount,
            total_invested=total_invested.amount,
            total_yield=total_yield.amount,
            total_yield_percentage=total_yield_pct,
            allocation=allocation,
            investments=investment_analytics_list,
            calculated_at=datetime.utcnow(),
        )