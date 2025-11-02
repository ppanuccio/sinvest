def create_test_portfolio(client, name="Test Portfolio", description="Test portfolio"):
    """Helper function to create a test portfolio."""
    from sinvest.models.portfolio import Portfolio
    portfolio_data = {'name': name, 'description': description}
    client.post('/portfolio/new', data=portfolio_data)
    return Portfolio.query.filter_by(name=name).first()

def create_test_investment(client, portfolio, symbol="AAPL", isin="US0378331005", 
                         quantity=10.0, price=150.0, date="2025-01-01"):
    """Helper function to create a test investment."""
    from sinvest.models.portfolio import Investment
    investment_data = {
        'symbol': symbol,
        'isin': isin,
        'currency': 'USD',
        'type': 'equity',
        'quantity': quantity,
        'purchase_price': price,
        'purchase_date': date
    }
    client.post(f'/portfolio/{portfolio.id}/add_investment', data=investment_data)
    return Investment.query.filter_by(isin=isin).first()