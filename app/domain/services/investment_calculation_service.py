"""Investment calculation service - pure business logic for investment calculations."""

from decimal import Decimal
from typing import List, Optional

from app.domain.entities.transaction import Transaction
from app.domain.entities.price_history import PriceHistory
from app.domain.value_objects import Money, Yield
from app.domain.exceptions import InvalidInvestmentException


class InvestmentCalculationService:
    """
    Stateless service that calculates investment metrics.
    All methods are pure functions - same input always produces same output.
    """

    @staticmethod
    def _is_coupon(transaction: Transaction) -> bool:
        """Return True when the transaction is a coupon receipt (not a buy)."""
        # Defensive: entities created before the `kind` field existed carry no
        # attribute; defaulting to "buy" preserves their behaviour.
        return getattr(transaction, "kind", "buy") == "coupon"

    @staticmethod
    def calculate_total_quantity(transactions: List[Transaction]) -> Decimal:
        """
        Calculate total quantity across all BUY transactions.
        Coupon transactions carry a quantity (the holding) but must NOT be
        summed into total quantity — they represent income, not acquisition.
        Returns 0 if no transactions.
        """
        total = Decimal("0")
        for transaction in transactions:
            if InvestmentCalculationService._is_coupon(transaction):
                continue
            total += transaction.quantity.value

        if total < 0:
            raise InvalidInvestmentException(
                "Total quantity cannot be negative"
            )

        return total

    @staticmethod
    def calculate_initial_amount(
        transactions: List[Transaction],
    ) -> Optional[Money]:
        """
        Get the initial amount from the first BUY transaction (by date).
        Coupon transactions are income, not acquisition, so they never form
        the capital basis. Returns None if there are no transactions at all
        or no BUY transactions.
        """
        if not transactions:
            return None

        # Coupons are income — exclude them from the capital basis.
        buys = [
            t
            for t in transactions
            if not InvestmentCalculationService._is_coupon(t)
        ]
        if not buys:
            return None

        # Sort by date to find the first BUY
        sorted_tx = sorted(buys, key=lambda t: t.date)
        return sorted_tx[0].amount

    @staticmethod
    def _convert_amount(
        amount: Money, reference_currency: str, rates: dict[str, Decimal]
    ) -> Money:
        """Convert a Money amount to the reference currency using provided rates."""
        if amount.currency == reference_currency:
            return amount
        rate = rates.get(amount.currency)
        if rate is None:
            raise InvalidInvestmentException(
                f"No exchange rate found for {amount.currency}→{reference_currency}"
            )
        return amount.convert_to(reference_currency, rate)

    @staticmethod
    def calculate_total_invested_amount(
        transactions: List[Transaction],
        reference_currency: str = "USD",
        rates: dict[str, Decimal] | None = None,
    ) -> Money:
        """
        Calculate total amount invested (sum of BUY transaction amounts).
        Coupon transactions are EXCLUDED: they represent income received, not
        capital paid in. All amounts are converted to reference_currency using
        the provided rates.
        """
        if not transactions:
            return Money(Decimal("0"))

        if rates is None:
            rates = {}

        total = Decimal("0")

        for transaction in transactions:
            if InvestmentCalculationService._is_coupon(transaction):
                continue
            converted = InvestmentCalculationService._convert_amount(
                transaction.amount, reference_currency, rates
            )
            total += converted.amount

        return Money(total, reference_currency)

    @staticmethod
    def calculate_total_value(
        transactions: List[Transaction],
        current_price: Money,
        reference_currency: str = "USD",
        rates: dict[str, Decimal] | None = None,
    ) -> Money:
        """
        Calculate current total value of the investment.
        Formula: (current_price × total_quantity) - sum(transaction_amounts)

        All amounts are converted to reference_currency using the provided rates.
        """
        if not transactions:
            return Money(Decimal("0"))

        if rates is None:
            rates = {}

        try:
            total_qty = InvestmentCalculationService.calculate_total_quantity(
                transactions
            )
            total_invested = (
                InvestmentCalculationService.calculate_total_invested_amount(
                    transactions, reference_currency, rates
                )
            )

            # Convert current price to reference currency
            converted_price = InvestmentCalculationService._convert_amount(
                current_price, reference_currency, rates
            )

            # Calculate: (price × quantity) - sum(amounts)
            current_value = converted_price * total_qty
            net_value = current_value - total_invested

            return net_value

        except ValueError as e:
            raise InvalidInvestmentException(f"Calculation error: {str(e)}")

    @staticmethod
    def calculate_yield(
        total_value: Money,
        initial_amount: Optional[Money],
    ) -> Yield:
        """
        Calculate yield (profit/loss).
        Since total_value is already the net profit/loss relative to invested amount,
        the yield is represented by the total_value amount.
        """
        if initial_amount is None or initial_amount.is_zero:
            return Yield(total_value.amount)

        if total_value.currency != initial_amount.currency:
            raise InvalidInvestmentException(
                f"Currency mismatch in yield calculation"
            )

        return Yield(total_value.amount)

    @staticmethod
    def calculate_yield_percentage(
        yield_value: Yield,
        initial_amount: Optional[Money],
    ) -> Optional[Decimal]:
        """
        Calculate yield as a percentage.
        Formula: (yield / initial_amount) × 100

        Returns None if no initial amount or initial amount is 0.
        """
        if initial_amount is None or initial_amount.is_zero:
            return None

        if initial_amount.amount <= 0:
            return None

        percentage = (yield_value.amount / initial_amount.amount) * 100

        return percentage

    @staticmethod
    def calculate_total_coupon_income(
        transactions: List[Transaction],
        reference_currency: str = "USD",
        rates: dict[str, Decimal] | None = None,
    ) -> Money:
        """
        Sum the amount of all COUPON transactions (income received).
        All amounts are converted to reference_currency using the provided rates.
        Returns Money(Decimal("0")) when there are no coupons.
        """
        if rates is None:
            rates = {}

        total = Decimal("0")
        for transaction in transactions:
            if not InvestmentCalculationService._is_coupon(transaction):
                continue
            converted = InvestmentCalculationService._convert_amount(
                transaction.amount, reference_currency, rates
            )
            total += converted.amount

        return Money(total, reference_currency)

    @staticmethod
    def calculate_total_value_bond(
        transactions: List[Transaction],
        face_value: Money,
        reference_currency: str = "USD",
        rates: dict[str, Decimal] | None = None,
    ) -> Money:
        """
        Compute total value / yield for a held-to-maturity bond.

        Formula: (face_value_per_unit x buy_quantity) - total_invested + coupons
        i.e. redemption value (face value basis) minus what was paid in, plus
        all coupon income received.

        Unlike calculate_total_value, this does NOT depend on a live market
        price — the bond redeems at its face value.

        All amounts are converted to reference_currency using the provided rates.
        """
        if not transactions:
            return Money(Decimal("0"))

        if rates is None:
            rates = {}

        buy_quantity = InvestmentCalculationService.calculate_total_quantity(
            transactions
        )
        # face_value is per-unit; redemption = face_value * quantity (face currency)
        redemption = face_value * buy_quantity
        redemption_ref = InvestmentCalculationService._convert_amount(
            redemption, reference_currency, rates
        )
        invested_ref = (
            InvestmentCalculationService.calculate_total_invested_amount(
                transactions, reference_currency, rates
            )
        )
        coupons_ref = InvestmentCalculationService.calculate_total_coupon_income(
            transactions, reference_currency, rates
        )

        return Money(redemption_ref.amount - invested_ref.amount + coupons_ref.amount, reference_currency)

    @staticmethod
    def get_price_per_unit(
        transactions: List[Transaction],
    ) -> Optional[Decimal]:
        """
        Get the weighted average price per unit across all BUY transactions.
        Coupon transactions are income received, not purchase cost, so they
        are excluded. If multiple transactions at different prices, calculates
        weighted average.
        """
        if not transactions:
            return None

        total_cost = Decimal("0")
        total_qty = Decimal("0")

        for transaction in transactions:
            if InvestmentCalculationService._is_coupon(transaction):
                continue
            total_cost += transaction.amount.amount
            total_qty += transaction.quantity.value

        if total_qty == 0:
            return None

        return total_cost / total_qty

    @staticmethod
    def get_latest_price_from_history(
        price_history: List[PriceHistory],
    ) -> Optional[Money]:
        """Get the most recent price from price history."""
        if not price_history:
            return None

        # Assuming price_history is sorted by date descending
        return price_history[0].price
