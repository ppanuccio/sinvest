"""Test configuration file for pytest

Provides pytest fixtures to run tests against an in-memory SQLite database
so tests are isolated and side-effect free.
"""
import pytest

from sinvest.app import create_app
from sinvest.repositories.sqlalchemy_impl import db as _db
from sinvest.models.portfolio import Portfolio, Investment
from datetime import datetime


@pytest.fixture(scope="session")
def app():
    """Session-scoped Flask app configured for testing (DB is per-test)."""
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    return app


@pytest.fixture()
def db(app):
    """Function-scoped DB fixture: create/drop all tables for each test for full isolation.

    This is slower than a session-scoped in-memory DB but guarantees no cross-test
    interference (recommended for tests that mutate DB state).
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def portfolio_factory(db):
    """Return a factory function to create Portfolio rows in the test DB.

    Usage:
        p = portfolio_factory(name='My P', description='desc')
    """
    def _create(name="Test Portfolio", description="", **kwargs):
        p = Portfolio(name=name, description=description, created_at=datetime.utcnow(), **kwargs)
        db.session.add(p)
        db.session.commit()
        return p

    return _create


@pytest.fixture()
def investment_factory(db, portfolio_factory):
    """Return a factory to create investments attached to a portfolio.

    Usage:
        inv = investment_factory(portfolio=p, isin='US000000', symbol='AAPL', currency='USD', quantity=1, purchase_price=10)
    If `portfolio` not provided, creates one via portfolio_factory.
    """
    def _create(portfolio=None, symbol="TEST", isin="TESTISIN", currency="USD", type_="STOCK",
                quantity=1.0, purchase_price=1.0, purchase_date=None, **kwargs):
        if portfolio is None:
            portfolio = portfolio_factory()
        if purchase_date is None:
            purchase_date = datetime.utcnow()
        inv = Investment(
            portfolio_id=portfolio.id,
            symbol=symbol,
            isin=isin,
            currency=currency,
            type=type_,
            quantity=quantity,
            purchase_price=purchase_price,
            purchase_date=purchase_date,
            created_at=datetime.utcnow(),
        )
        db.session.add(inv)
        db.session.commit()
        return inv

    return _create