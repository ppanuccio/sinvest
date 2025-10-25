"""Main Flask application module"""
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import yfinance as yf

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portfolio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


def create_app(config: dict | None = None) -> Flask:
    """Application factory for tests and programmatic use.

    Keeps backward compatibility by returning the module-level `app` instance
    after applying any provided configuration overrides.
    """
    if config:
        app.config.update(config)
    return app

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import models after db initialization to avoid circular imports
from sinvest.models.portfolio import Portfolio as PortfolioModel, Investment as InvestmentModel
from sinvest.repositories.sqlalchemy_impl import SQLAlchemyPortfolioRepository
from sinvest.domain.services import compute_investment_values, aggregate_portfolio

# Repository instance (persistence implementation)
repo = SQLAlchemyPortfolioRepository()

@app.route('/')
def index():
    """Home page route"""
    portfolios = repo.list_portfolios()
    return render_template('index.html', portfolios=portfolios)

@app.route('/portfolio/new', methods=['GET', 'POST'])
def new_portfolio():
    """Create new portfolio route"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        p = repo.add_portfolio(name=name, description=description)
        flash('Portfolio created successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('portfolio_form.html')

@app.route('/portfolio/<int:portfolio_id>')
def view_portfolio(portfolio_id):
    """View portfolio details route (thin controller)."""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        from flask import abort
        abort(404)

    # Compose display data using domain services so templates are presentation-only
    totals_by_currency, gains_by_currency = aggregate_portfolio(portfolio)

    investments_display = []
    for inv in portfolio.investments:
        vals = compute_investment_values(inv)
        investments_display.append({
            'id': inv.id,
            'symbol': inv.symbol,
            'isin': inv.isin,
            'type': inv.type,
            'quantity': inv.quantity,
            'currency': inv.currency,
            'purchase_price': inv.purchase_price,
            'current_price': vals['current_price'],
            'current_value': vals['current_value'],
            'gain_loss': vals['gain_loss'],
        })

    return render_template('portfolio_detail.html', 
                         portfolio=portfolio,
                         investments=investments_display,
                         totals_by_currency=totals_by_currency,
                         gains_by_currency=gains_by_currency)

@app.route('/portfolio/<int:portfolio_id>/add_investment', methods=['GET', 'POST'])
def add_investment(portfolio_id):
    """Add investment to portfolio route"""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        from flask import abort
        abort(404)

    if request.method == 'POST':
        symbol = request.form.get('symbol')
        isin = request.form.get('isin')
        currency = request.form.get('currency') or 'USD'
        investment_type = request.form.get('type')
        quantity = float(request.form.get('quantity'))
        purchase_price = float(request.form.get('purchase_price'))
        purchase_date = datetime.strptime(request.form.get('purchase_date'), '%Y-%m-%d')
        # Prevent adding duplicate ISINs within the same portfolio
        existing_port = repo.get_portfolio(portfolio_id)
        if existing_port and any(i.isin == isin for i in existing_port.investments):
            flash('An investment with this ISIN already exists in the portfolio.', 'warning')
            return redirect(url_for('view_portfolio', portfolio_id=portfolio_id))

        # Build domain entity and persist through repository
        from sinvest.domain.entities import InvestmentEntity
        inv_entity = InvestmentEntity(
            id=None,
            portfolio_id=portfolio_id,
            symbol=symbol,
            isin=isin,
            currency=currency,
            type=investment_type,
            quantity=quantity,
            purchase_price=purchase_price,
            purchase_date=purchase_date,
        )

        repo.add_investment(inv_entity)
        
        flash('Investment added successfully!', 'success')
        return redirect(url_for('view_portfolio', portfolio_id=portfolio_id))

    return render_template('investment_form.html', portfolio=portfolio)

@app.route('/portfolio/<int:portfolio_id>/investment/<int:investment_id>/delete', methods=['POST'])
def delete_investment(portfolio_id, investment_id):
    """Delete an investment from a portfolio"""
    inv = InvestmentModel.query.get_or_404(investment_id)
    
    # Verify investment belongs to the specified portfolio
    if inv.portfolio_id != portfolio_id:
        flash('Invalid investment or portfolio.', 'error')
        return redirect(url_for('index'))
    
    repo.delete_investment(investment_id)
    
    flash('Investment deleted successfully.', 'success')
    return redirect(url_for('view_portfolio', portfolio_id=portfolio_id))

@app.route('/portfolio/<int:portfolio_id>/delete', methods=['POST'])
def delete_portfolio(portfolio_id):
    """Delete a portfolio and all its investments"""
    p = PortfolioModel.query.get_or_404(portfolio_id)
    repo.delete_portfolio(portfolio_id)
    
    flash('Portfolio and all its investments deleted successfully.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)