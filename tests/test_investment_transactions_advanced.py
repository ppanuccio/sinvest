"""Additional test cases for investment transactions."""
from datetime import datetime, timedelta
import pytest
from sinvest.models.portfolio import Investment, Portfolio, Transaction
from test_helpers import create_test_portfolio, create_test_investment


def test_selling_transaction(client, db):
    """Test that selling transactions (negative quantity) work correctly."""
    # Create initial investment with 10 shares
    portfolio = create_test_portfolio(client)
    investment = create_test_investment(client, portfolio, quantity=10.0, price=100.0)
    
    # Add a sell transaction for 4 shares
    sell_data = {
        'quantity': -4.0,  # Negative quantity for selling
        'unit_price': 120.0,  # Selling at a higher price
        'transaction_date': '2025-02-01'
    }
    client.post(f'/portfolio/{portfolio.id}/investment/{investment.id}/transaction', data=sell_data)
    
    # Verify final quantity and calculations
    investment = Investment.query.get(investment.id)  # Refresh from DB
    total_quantity = sum(t.quantity for t in investment.transactions)
    assert total_quantity == 6.0  # Initial 10 - Sold 4
    
    # Verify cost basis calculation
    # Initial investment: 10 shares * $100 = $1000
    # Sold 4 shares * $120 = -$480 (negative because it's a sale)
    expected_cost = (10.0 * 100.0) + (-4.0 * 120.0)
    cost_basis = sum(t.quantity * t.unit_price for t in investment.transactions)
    assert cost_basis == expected_cost


def test_multiple_mixed_transactions(client, db):
    """Test multiple buy and sell transactions in mixed order."""
    portfolio = create_test_portfolio(client)
    investment = create_test_investment(client, portfolio, quantity=5.0, price=100.0)
    
    # Series of transactions
    transactions = [
        {'quantity': 3.0, 'unit_price': 110.0, 'transaction_date': '2025-02-01'},  # Buy 3
        {'quantity': -2.0, 'unit_price': 120.0, 'transaction_date': '2025-02-15'},  # Sell 2
        {'quantity': 4.0, 'unit_price': 90.0, 'transaction_date': '2025-03-01'},   # Buy 4
        {'quantity': -1.0, 'unit_price': 130.0, 'transaction_date': '2025-03-15'}  # Sell 1
    ]
    
    for tx in transactions:
        client.post(f'/portfolio/{portfolio.id}/investment/{investment.id}/transaction', data=tx)
    
    # Verify final quantity (5 + 3 - 2 + 4 - 1 = 9)
    investment = Investment.query.get(investment.id)
    total_quantity = sum(t.quantity for t in investment.transactions)
    assert total_quantity == 9.0
    
    # Verify all transactions are recorded in correct order
    assert len(investment.transactions) == 5  # Initial + 4 additional
    dates = [tx.transaction_date.strftime('%Y-%m-%d') for tx in investment.transactions]
    assert dates == ['2025-01-01', '2025-02-01', '2025-02-15', '2025-03-01', '2025-03-15']


def test_zero_quantity_validation(client, db):
    """Test that zero quantity transactions are not allowed."""
    portfolio = create_test_portfolio(client)
    investment = create_test_investment(client, portfolio)
    
    # Try to add a zero quantity transaction
    zero_tx = {
        'quantity': 0.0,
        'unit_price': 100.0,
        'transaction_date': '2025-02-01'
    }
    response = client.post(
        f'/portfolio/{portfolio.id}/investment/{investment.id}/transaction', 
        data=zero_tx,
        follow_redirects=True
    )
    
    # Verify only initial transaction exists
    investment = Investment.query.get(investment.id)
    assert len(investment.transactions) == 1


def test_future_date_validation(client, db):
    """Test that future transaction dates are not allowed."""
    portfolio = create_test_portfolio(client)
    investment = create_test_investment(client, portfolio)
    
    # Try to add a transaction with future date
    future_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    future_tx = {
        'quantity': 1.0,
        'unit_price': 100.0,
        'transaction_date': future_date
    }
    response = client.post(
        f'/portfolio/{portfolio.id}/investment/{investment.id}/transaction', 
        data=future_tx,
        follow_redirects=True
    )
    
    # Verify only initial transaction exists
    investment = Investment.query.get(investment.id)
    assert len(investment.transactions) == 1


def test_multiple_investments_transactions(client, db):
    """Test transactions across multiple investments in the same portfolio."""
    portfolio = create_test_portfolio(client)
    
    # Create two investments
    inv1 = create_test_investment(
        client, portfolio, 
        symbol="AAPL", isin="US0378331005",
        quantity=10.0, price=150.0
    )
    inv2 = create_test_investment(
        client, portfolio,
        symbol="MSFT", isin="US5949181045",
        quantity=5.0, price=200.0
    )
    
    # Add transactions to both investments
    tx1 = {
        'quantity': 2.0,
        'unit_price': 160.0,
        'transaction_date': '2025-02-01'
    }
    tx2 = {
        'quantity': 3.0,
        'unit_price': 210.0,
        'transaction_date': '2025-02-01'
    }
    
    client.post(f'/portfolio/{portfolio.id}/investment/{inv1.id}/transaction', data=tx1)
    client.post(f'/portfolio/{portfolio.id}/investment/{inv2.id}/transaction', data=tx2)
    
    # Verify each investment has correct transactions and totals
    inv1 = Investment.query.get(inv1.id)
    inv2 = Investment.query.get(inv2.id)
    
    assert sum(t.quantity for t in inv1.transactions) == 12.0  # 10 + 2
    assert sum(t.quantity for t in inv2.transactions) == 8.0   # 5 + 3
    
    # Verify transactions didn't cross between investments
    assert all(t.investment_id == inv1.id for t in inv1.transactions)
    assert all(t.investment_id == inv2.id for t in inv2.transactions)