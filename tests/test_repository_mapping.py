from datetime import datetime

from sinvest.models.portfolio import Portfolio as PortfolioModel, Investment as InvestmentModel
from sinvest.repositories.sqlalchemy_impl import SQLAlchemyPortfolioRepository


def test_repository_maps_models_to_entities(app, db):
    repo = SQLAlchemyPortfolioRepository()

    # Create a portfolio model
    p = PortfolioModel(name='Repo Mapping Test', description='desc')
    db.session.add(p)
    db.session.commit()

    # Create an investment model linked to portfolio
    inv = InvestmentModel(
        portfolio_id=p.id,
        symbol='TEST',
        isin='TT0000000001',
        currency='USD',
        type='equity',
        quantity=3.0,
        purchase_price=5.0,
        purchase_date=datetime(2021, 1, 1),
    )
    db.session.add(inv)
    db.session.commit()

    # Use repository to fetch and map
    pe = repo.get_portfolio(p.id)
    assert pe is not None
    assert pe.name == p.name
    assert pe.description == p.description
    assert len(pe.investments) == 1

    ie = pe.investments[0]
    assert ie.symbol == inv.symbol
    assert ie.isin == inv.isin
    assert ie.currency == inv.currency
    assert ie.quantity == inv.quantity
    assert ie.purchase_price == inv.purchase_price

    # Cleanup
    repo.delete_portfolio(p.id)