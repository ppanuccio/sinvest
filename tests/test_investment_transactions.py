"""Test investment transactions and quantity/value calculations."""
from datetime import datetime, timedelta
from decimal import Decimal
from sinvest.models.portfolio import Investment, Portfolio, Transaction
import pytest


def test_investment_creates_initial_transaction(client, db):
    """Test that creating a new investment automatically creates an initial transaction."""
    # Create a portfolio first
    portfolio_data = {
        'name': 'Test Portfolio',
        'description': 'Test portfolio for transactions'
    }
    portfolio_resp = client.post('/portfolio/new', data=portfolio_data)
    portfolio = Portfolio.query.first()
    assert portfolio is not None

    # Investment data
    investment_data = {
        'symbol': 'AAPL',
        'isin': 'US0378331005',
        'currency': 'USD',
        'type': 'equity',
        'quantity': 10.0,
        'purchase_price': 150.0,
        'purchase_date': '2025-01-01'
    }

    # Create investment via POST
    resp = client.post(f'/portfolio/{portfolio.id}/add_investment', data=investment_data)
    assert resp.status_code == 302  # Redirect after successful creation

    # Get the created investment
    investment = Investment.query.filter_by(isin=investment_data['isin']).first()
    assert investment is not None

    # Verify initial transaction was created
    assert len(investment.transactions) == 1
    initial_tx = investment.transactions[0]
    assert initial_tx.quantity == investment_data['quantity']
    assert initial_tx.unit_price == investment_data['purchase_price']
    assert initial_tx.transaction_date.strftime('%Y-%m-%d') == investment_data['purchase_date']
    assert initial_tx.investment_id == investment.id

def test_investment_total_matches_transactions(client, db):
    """Test that investment total quantity and value match transaction calculations."""
    # Create portfolio
    portfolio_data = {
        'name': 'Test Portfolio',
        'description': 'Test portfolio for transaction totals'
    }
    portfolio_resp = client.post('/portfolio/new', data=portfolio_data)
    portfolio = Portfolio.query.first()

    # Create investment
    investment_data = {
        'symbol': 'GOOGL',
        'isin': 'US02079K1079',
        'currency': 'USD',
        'type': 'equity',
        'quantity': 5.0,
        'purchase_price': 120.0,
        'purchase_date': '2025-01-01'
    }
    client.post(f'/portfolio/{portfolio.id}/add_investment', data=investment_data)
    investment = Investment.query.filter_by(isin=investment_data['isin']).first()

    # Add additional transaction
    transaction_data = {
        'quantity': 3.0,
        'unit_price': 125.0,
        'transaction_date': '2025-02-01'
    }
    client.post(f'/portfolio/{portfolio.id}/investment/{investment.id}/transaction', data=transaction_data)

    # Verify totals
    investment = Investment.query.filter_by(isin=investment_data['isin']).first()
    total_quantity = sum(t.quantity for t in investment.transactions)
    assert total_quantity == 8.0  # Initial 5 + Additional 3

    # Verify cost basis calculation
    expected_cost = (5.0 * 120.0) + (3.0 * 125.0)  # Initial transaction + Additional transaction
    cost_basis = sum(t.quantity * t.unit_price for t in investment.transactions)
    assert cost_basis == expected_cost

def test_transaction_deletion_updates_totals(client, db):
    """Test that deleting a transaction correctly updates investment totals."""
    # Create portfolio
    portfolio_data = {
        'name': 'Test Portfolio',
        'description': 'Test portfolio for transaction deletion'
    }
    portfolio_resp = client.post('/portfolio/new', data=portfolio_data)
    portfolio = Portfolio.query.first()

    # Create investment
    investment_data = {
        'symbol': 'MSFT',
        'isin': 'US5949181045',
        'currency': 'USD',
        'type': 'equity',
        'quantity': 10.0,
        'purchase_price': 200.0,
        'purchase_date': '2025-01-01'
    }
    client.post(f'/portfolio/{portfolio.id}/add_investment', data=investment_data)
    investment = Investment.query.filter_by(isin=investment_data['isin']).first()

    # Add second transaction
    transaction_data = {
        'quantity': 5.0,
        'unit_price': 210.0,
        'transaction_date': '2025-02-01'
    }
    client.post(f'/portfolio/{portfolio.id}/investment/{investment.id}/transaction', data=transaction_data)

    # Get the second transaction
    second_transaction = Transaction.query.filter_by(
        investment_id=investment.id,
        quantity=transaction_data['quantity']
    ).first()

    # Delete the second transaction
    client.post(f'/investment/{investment.id}/transaction/{second_transaction.id}/delete')

    # Verify totals after deletion
    investment = Investment.query.filter_by(isin=investment_data['isin']).first()
    total_quantity = sum(t.quantity for t in investment.transactions)
    assert total_quantity == 10.0  # Should only have initial quantity

    # Verify cost basis after deletion
    cost_basis = sum(t.quantity * t.unit_price for t in investment.transactions)
    assert cost_basis == investment_data['quantity'] * investment_data['purchase_price']