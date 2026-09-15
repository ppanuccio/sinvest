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
        reference_currency: str = "USD",
        rates: dict[str, Decimal] | None = None,
    ) -> tuple[Money, Money, Yield, Optional[Decimal]]:
        """
        Calculate portfolio-level totals.
        All amounts are converted to reference_currency using the provided rates.

        Total value is what the holdings are WORTH (position values: market
        price × quantity, face-value redemption for HTM bonds, or the invested
        cost when no price is available). Total invested sums every BUY across
        ALL holdings. Total yield (gain/loss) is the total return — value gained
        plus income received — so it satisfies the identity
        gain = total_value − total_invested + coupon_income.

        Returns: (total_current_value, total_invested, total_yield, total_yield_percentage)
        """
        if not investments:
            return (
                Money(Decimal("0")),
                Money(Decimal("0")),
                Yield(Decimal("0")),
                None,
            )

        if rates is None:
            rates = {}

        total_value = Decimal("0")
        total_invested = Decimal("0")
        total_yield = Decimal("0")

        for investment in investments:
            transactions = transactions_by_investment.get(investment.id, [])
            price_history = price_history_by_investment.get(
                investment.id, []
            )
            if not transactions:
                continue

            # A held-to-maturity bond is valued on its face value basis even
            # without a live market price.
            is_bond_htm = (
                investment.held_to_maturity
                and investment.face_value is not None
                and bool(transactions)
            )

            try:
                invested = (
                    InvestmentCalculationService.calculate_total_invested_amount(
                        transactions, reference_currency, rates
                    )
                )
                coupons = (
                    InvestmentCalculationService.calculate_total_coupon_income(
                        transactions, reference_currency, rates
                    )
                )
                if is_bond_htm:
                    face_value = investment.face_value
                    assert face_value is not None  # implied by is_bond_htm
                    position = (
                        InvestmentCalculationService.calculate_position_value(
                            transactions,
                            face_value,
                            reference_currency,
                            rates,
                        )
                    )
                    gain = (
                        InvestmentCalculationService.calculate_total_value_bond(
                            transactions,
                            face_value,
                            reference_currency,
                            rates,
                        )
                    )
                elif price_history:
                    current_price = price_history[0].price  # Latest price
                    position = (
                        InvestmentCalculationService.calculate_position_value(
                            transactions,
                            current_price,
                            reference_currency,
                            rates,
                        )
                    )
                    gain = InvestmentCalculationService.calculate_total_value(
                        transactions, current_price, reference_currency, rates
                    )
                else:
                    # No live price: the invested cost estimates the holding's
                    # worth, so the only known gain is the income received.
                    position = invested
                    gain = coupons
            except Exception:
                # Skip this investment — can't calculate
                continue

            total_value += position.amount
            total_invested += invested.amount
            total_yield += gain.amount

        total_value_obj = Money(total_value, reference_currency)
        total_invested_obj = Money(total_invested, reference_currency)
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
        reference_currency: str = "USD",
        rates: dict[str, Decimal] | None = None,
    ) -> Dict[str, Decimal]:
        """
        Calculate allocation percentages for each investment.

        Weights are based on each holding's POSITION value — market price ×
        quantity, face-value redemption for held-to-maturity bonds, or the
        invested cost when no price is available — NOT the net gain. Net
        values can be negative or dwarf the actual holding size, which would
        produce meaningless weights (e.g. >100% or negative).

        All amounts are converted to reference_currency using the provided rates.
        Returns: {investment_id: percentage}
        """
        allocation: Dict[str, Decimal] = {}

        if not investments:
            return allocation

        if rates is None:
            rates = {}

        total_value = Decimal("0")
        investment_values = {}

        for investment in investments:
            transactions = transactions_by_investment.get(investment.id, [])
            price_history = price_history_by_investment.get(
                investment.id, []
            )

            is_bond_htm = (
                investment.held_to_maturity
                and investment.face_value is not None
                and bool(transactions)
            )

            try:
                if is_bond_htm:
                    face_value = investment.face_value
                    assert face_value is not None  # implied by is_bond_htm
                    position = (
                        InvestmentCalculationService.calculate_position_value(
                            transactions,
                            face_value,
                            reference_currency,
                            rates,
                        )
                    )
                elif price_history:
                    position = (
                        InvestmentCalculationService.calculate_position_value(
                            transactions,
                            price_history[0].price,
                            reference_currency,
                            rates,
                        )
                    )
                else:
                    # No live price: the invested cost is the best available
                    # estimate of what the holding is worth.
                    position = (
                        InvestmentCalculationService.calculate_total_invested_amount(
                            transactions, reference_currency, rates
                        )
                    )
                investment_values[investment.id] = position.amount
                total_value += position.amount
            except Exception:
                investment_values[investment.id] = Decimal("0")

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
