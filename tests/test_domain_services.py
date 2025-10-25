from datetime import datetime
from sinvest.domain.entities import InvestmentEntity, PortfolioEntity
from sinvest.domain.price_provider import MockPriceProvider
from sinvest.domain.services import compute_investment_values, aggregate_portfolio


def test_compute_investment_values_basic():
    provider = MockPriceProvider(mapping={"FOO": 10.0}, default=0.0)
    inv = InvestmentEntity(
        id=None,
        portfolio_id=1,
        symbol="FOO",
        isin="XX0000000001",
        currency="USD",
        type="equity",
        quantity=2.0,
        purchase_price=8.0,
        purchase_date=datetime(2020, 1, 1),
    )

    vals = compute_investment_values(inv, provider)
    assert vals["current_price"] == 10.0
    assert vals["current_value"] == 20.0
    assert vals["gain_loss"] == 4.0


def test_aggregate_portfolio_multiple_currencies():
    provider = MockPriceProvider(mapping={"A": 5.0, "B": 2.0}, default=1.0)

    inv1 = InvestmentEntity(None, 1, "A", "AA0000000001", "USD", "equity", 10, 3.0, datetime(2020,1,1))
    inv2 = InvestmentEntity(None, 1, "B", "BB0000000002", "EUR", "etf", 5, 1.0, datetime(2020,1,1))

    portfolio = PortfolioEntity(id=1, name="P", description="d", created_at=None, investments=[inv1, inv2])
    totals, gains = aggregate_portfolio(portfolio, provider)

    # inv1: current=10*5=50, initial=10*3=30 -> gain 20 (USD)
    # inv2: current=5*2=10, initial=5*1=5 -> gain 5 (EUR)
    assert totals["USD"] == 50.0
    assert totals["EUR"] == 10.0
    assert gains["USD"] == 20.0
    assert gains["EUR"] == 5.0
