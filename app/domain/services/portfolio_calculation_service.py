"""Portfolio calculation service - aggregated portfolio metrics."""

from decimal import Decimal
from typing import List, Dict, Optional

from app.domain.entities.investment import Investment
from app.domain.entities.transaction import Transaction
from app.domain.entities.price_history import PriceHistory
from app.domain.value_objects import Money, Yield
from app.domain.exceptions import InvalidPortfolioException
from app.domain.services.investment_calculation_service import (
    InvestmentCalculationService,
)


class PortfolioCalculationService:
    """
    Stateless service for portfolio-level calculations.
    Aggregates metrics across multiple investments.
    """

    @staticmethod
    def calculate_portfolio_totals(
        investments: List[Investment],
        transactions_by_investment: Dict[str, List[Transaction]],
        price_history_by_investment: Dict[str, List[PriceHistory]],
    ) -> tuple[Money, Money, Yield, Optional[Decimal]]:
        """
        Calculate portfolio-level totals.
        Returns: (total_current_value, total_invested, total_yield, total_yield_percentage)
        """
        if not investments:
            return (
                Money(Decimal("0")),
                Money(Decimal("0")),
                Yield(Decimal("0")),
                None,
            )

        total_value = Decimal("0")
        total_invested = Decimal("0")
        total_yield = Decimal("0")
        currency = None

        for investment in investments:
            transactions = transactions_by_investment.get(investment.id, [])
            price_history = price_history_by_investment.get(
                investment.id, []
            )

            if not price_history:
                # Cannot calculate value without price
                continue

            current_price = price_history[0].price  # Latest price

            # Calculate investment metrics
            inv_value = InvestmentCalculationService.calculate_total_value(
                transactions, current_price
            )
            inv_invested = (
                InvestmentCalculationService.calculate_total_invested_amount(
                    transactions
                )
            )
            initial_amount = (
                InvestmentCalculationService.calculate_initial_amount(
                    transactions
                )
            )
            inv_yield = InvestmentCalculationService.calculate_yield(
                inv_value, initial_amount
            )

            # Set currency from first investment
            if currency is None:
                currency = current_price.currency
            elif currency != current_price.currency:
                raise InvalidPortfolioException(
                    f"Mixed currencies in portfolio: {currency} and {current_price.currency}"
                )

            total_value += inv_value.amount
            total_invested += inv_invested.amount
            total_yield += inv_yield.amount

        if currency is None:
            currency = "USD"

        total_value_obj = Money(total_value, currency)
        total_invested_obj = Money(total_invested, currency)
        total_yield_obj = Yield(total_yield)

        # Calculate portfolio yield percentage
        total_yield_pct = None
        if total_invested_obj.amount > 0:
            total_yield_pct = (total_yield / total_invested_obj.amount) * 100

        return (total_value_obj, total_invested_obj, total_yield_obj, total_yield_pct)

    @staticmethod
    def calculate_allocation_percentages(
        investments: List[Investment],
        transactions_by_investment: Dict[str, List[Transaction]],
        price_history_by_investment: Dict[str, List[PriceHistory]],
    ) -> Dict[str, Decimal]:
        """
        Calculate allocation percentages for each investment.
        Returns: {investment_id: percentage}
        """
        allocation = {}

        if not investments:
            return allocation

        total_value = Decimal("0")
        investment_values = {}

        for investment in investments:
            transactions = transactions_by_investment.get(investment.id, [])
            price_history = price_history_by_investment.get(
                investment.id, []
            )

            if not price_history:
                investment_values[investment.id] = Decimal("0")
                continue

            current_price = price_history[0].price
            inv_value = InvestmentCalculationService.calculate_total_value(
                transactions, current_price
            )

            investment_values[investment.id] = inv_value.amount
            total_value += inv_value.amount

        # Calculate percentages
        if total_value > 0:
            for investment_id, value in investment_values.items():
                percentage = (value / total_value) * 100
                allocation[investment_id] = percentage
        else:
            # All investments have 0 value - equal allocation
            if investments:
                equal_pct = Decimal("100") / Decimal(len(investments))
                for investment in investments:
                    allocation[investment.id] = equal_pct

        return allocation

    @staticmethod
    def calculate_portfolio_yield_percentage(
        total_yield: Yield,
        total_invested: Money,
    ) -> Optional[Decimal]:
        """Calculate portfolio yield as a percentage."""
        if total_invested.amount <= 0:
            return None

        return (total_yield.amount / total_invested.amount) * 100
