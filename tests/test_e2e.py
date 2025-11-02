def test_create_portfolio_e2e(client, db):
    """End-to-end test: create a portfolio via the HTTP POST route and verify it appears on the index page."""
    name = "E2E Portfolio"
    description = "End-to-end created portfolio"

    # Create portfolio via POST to the form route and follow redirect to index
    resp = client.post('/portfolio/new', data={
        'name': name,
        'description': description,
    }, follow_redirects=True)

    assert resp.status_code == 200
    # The index template should render the portfolio name
    assert name.encode() in resp.data
