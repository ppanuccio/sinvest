"""Domain services: business logic separated from persistence and presentation."""
from typing import Dict, Tuple, List
from .entities import InvestmentEntity, PortfolioEntity
from .price_provider import MarketPriceProvider, YFinancePriceProvider


def fetch_current_price(symbol: str, provider: MarketPriceProvider) -> float:
    """Fetch current price for a symbol using the provided provider."""
    try:
        return provider.get_price(symbol)
    except Exception:
        return 0.0


def compute_investment_values(inv: InvestmentEntity, provider: MarketPriceProvider | None = None) -> Dict:
    """Compute current price/value/gain for a single investment entity.

    Accepts a MarketPriceProvider to fetch current prices. If none provided,
    uses the YFinancePriceProvider by default.

    Returns a dict with: current_price, current_value, gain_loss
    All values are expressed in the investment's own currency.
    """
    provider = provider or YFinancePriceProvider()
    price = fetch_current_price(inv.symbol, provider) or inv.purchase_price
    current_value = inv.quantity * price
    initial_value = inv.quantity * inv.purchase_price
    gain_loss = current_value - initial_value
    return {
        "current_price": price,
        "current_value": current_value,
        "gain_loss": gain_loss,
    }


def aggregate_portfolio(portfolio: PortfolioEntity, provider: MarketPriceProvider | None = None) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Aggregate totals and gains grouped by currency.

    Returns (totals_by_currency, gains_by_currency)
    """
    provider = provider or YFinancePriceProvider()
    totals = {}
    gains = {}
    for inv in portfolio.investments:
        vals = compute_investment_values(inv, provider)
        cur = (inv.currency or "USD").upper()
        totals[cur] = totals.get(cur, 0.0) + vals["current_value"]
        gains[cur] = gains.get(cur, 0.0) + vals["gain_loss"]
    return totals, gains
