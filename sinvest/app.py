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
from sinvest.models.portfolio import Transaction as TransactionModel
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
        return abort(404)

    # Compose display data using domain services so templates are presentation-only
    totals_by_currency, gains_by_currency = aggregate_portfolio(portfolio)

    import traceback, sys
    investments_display = []
    try:
        for inv in portfolio.investments:
            vals = compute_investment_values(inv)
            txs = []
            for t in (getattr(inv, 'transactions', []) or []):
                txs.append({
                    'id': getattr(t, 'id', None),
                    'quantity': getattr(t, 'quantity', 0.0) or 0.0,
                    'unit_price': getattr(t, 'unit_price', 0.0) or 0.0,
                    'transaction_date': t.transaction_date.strftime('%Y-%m-%d') if getattr(t, 'transaction_date', None) else '',
                    'created_at': t.created_at.strftime('%Y-%m-%d %H:%M:%S') if getattr(t, 'created_at', None) else '',
                })
            if txs:
                cost_basis = sum((t['quantity'] or 0.0) * (t['unit_price'] or 0.0) for t in txs)
                current_qty = sum((t['quantity'] or 0.0) for t in txs)
            else:
                cost_basis = (getattr(inv, 'purchase_price', 0.0) or 0.0) * (getattr(inv, 'quantity', 0.0) or 0.0)
                current_qty = getattr(inv, 'quantity', 0.0) or 0.0
            investments_display.append({
                'id': getattr(inv, 'id', None),
                'symbol': getattr(inv, 'symbol', ''),
                'isin': getattr(inv, 'isin', ''),
                'type': getattr(inv, 'type', ''),
                'quantity': getattr(inv, 'quantity', 0.0) or 0.0,
                'current_quantity': current_qty,
                'currency': getattr(inv, 'currency', 'USD') or 'USD',
                'purchase_price': getattr(inv, 'purchase_price', 0.0) or 0.0,
                'cost_basis': cost_basis,
                'current_price': vals.get('current_price', 0.0),
                'current_value': vals.get('current_value', 0.0),
                'gain_loss': vals.get('gain_loss', 0.0),
                'transactions': txs,
            })
        return render_template('portfolio_detail.html', 
                             portfolio=portfolio,
                             investments=investments_display,
                             totals_by_currency=totals_by_currency,
                             gains_by_currency=gains_by_currency)
    except Exception as e:
        print("\n--- ERROR in view_portfolio investments mapping ---", file=sys.stderr)
        traceback.print_exc()
        print("--- END ERROR ---\n", file=sys.stderr)
        from flask import abort
        return abort(500)


# --- Investment detail page ---
@app.route('/investment/<int:investment_id>')
def investment_detail(investment_id):
    inv = InvestmentModel.query.get_or_404(investment_id)
    portfolio = PortfolioModel.query.get(inv.portfolio_id)
    vals = compute_investment_values(inv)
    txs = inv.transactions or []
    cost_basis = sum((t.quantity or 0.0) * (t.unit_price or 0.0) for t in txs) if txs else (inv.purchase_price or 0.0) * (inv.quantity or 0.0)
    current_qty = sum((t.quantity or 0.0) for t in txs) if txs else inv.quantity
    return render_template('investment_detail.html', investment=inv, portfolio=portfolio, transactions=txs, cost_basis=cost_basis, current_qty=current_qty, vals=vals)


# --- Delete transaction ---
@app.route('/investment/<int:investment_id>/transaction/<int:transaction_id>/delete', methods=['POST'])
def delete_transaction(investment_id, transaction_id):
    tx = TransactionModel.query.get_or_404(transaction_id)
    db.session.delete(tx)
    db.session.commit()
    flash('Transaction deleted.', 'success')
    return redirect(url_for('investment_detail', investment_id=investment_id))

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
            return redirect(url_for('view_portfolio', portfolio_id=portfolio_id))

        # Build domain entity with initial transaction and persist through repository
        from sinvest.domain.entities import InvestmentEntity, TransactionEntity
        
        # Create initial transaction with the investment's purchase details
        initial_transaction = TransactionEntity(
            id=None,
            investment_id=None,  # Will be set after investment creation
            quantity=quantity,
            unit_price=purchase_price,
            transaction_date=purchase_date,
            created_at=None
        )
        
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
            transactions=[initial_transaction]  # Include initial transaction
        )

        repo.add_investment(inv_entity)
        
        flash('Investment added successfully with initial transaction!', 'success')
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


@app.route('/portfolio/<int:portfolio_id>/investment/<int:investment_id>/transaction', methods=['GET', 'POST'])
def add_transaction(portfolio_id, investment_id):
    """Record a buy (+quantity) or sell (-quantity) for an investment identified by ID.

    The user requested identification by ISIN; this route supports identification by
    investment id (for convenience) and repository also exposes add_transaction by
    portfolio+isin.

    Validations:
    - Quantity must not be zero
    - Transaction date must not be in the future
    """
    # Load investment record
    inv = InvestmentModel.query.get_or_404(investment_id)
    if request.method == 'POST':
        try:
            # quantity can be negative for sells
            quantity = float(request.form.get('quantity'))
            if quantity == 0:
                flash('Transaction quantity cannot be zero.', 'error')
                return render_template('transaction_form.html', investment=inv)

            unit_price = float(request.form.get('unit_price'))
            transaction_date = datetime.strptime(request.form.get('transaction_date'), '%Y-%m-%d')
            
            # Validate transaction date is not in the future
            if transaction_date.date() > datetime.now().date():
                flash('Transaction date cannot be in the future.', 'error')
                return render_template('transaction_form.html', investment=inv)
        except ValueError as e:
            flash('Invalid input values. Please check your entries.', 'error')
            return render_template('transaction_form.html', investment=inv)
        # Use repository to persist transaction (by portfolio + isin)
        repo.add_transaction(portfolio_id=portfolio_id, isin=inv.isin, quantity=quantity, unit_price=unit_price, transaction_date=transaction_date)
        flash('Transaction recorded successfully.', 'success')
        return redirect(url_for('view_portfolio', portfolio_id=portfolio_id))

    return render_template('transaction_form.html', investment=inv)

@app.route('/portfolio/<int:portfolio_id>/delete', methods=['POST'])
def delete_portfolio(portfolio_id):
    """Delete a portfolio and all its investments"""
    p = PortfolioModel.query.get_or_404(portfolio_id)
    repo.delete_portfolio(portfolio_id)
    
    flash('Portfolio and all its investments deleted successfully.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)