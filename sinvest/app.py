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

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import models after db initialization to avoid circular imports
from sinvest.models.portfolio import Portfolio, Investment

@app.route('/')
def index():
    """Home page route"""
    portfolios = Portfolio.query.all()
    return render_template('index.html', portfolios=portfolios)

@app.route('/portfolio/new', methods=['GET', 'POST'])
def new_portfolio():
    """Create new portfolio route"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        portfolio = Portfolio(name=name, description=description)
        db.session.add(portfolio)
        db.session.commit()
        
        flash('Portfolio created successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('portfolio_form.html')

@app.route('/portfolio/<int:portfolio_id>')
def view_portfolio(portfolio_id):
    """View portfolio details route"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    totals_by_currency = portfolio.get_total_value()
    gains_by_currency = portfolio.get_total_gain_loss()
    return render_template('portfolio_detail.html', 
                         portfolio=portfolio,
                         totals_by_currency=totals_by_currency,
                         gains_by_currency=gains_by_currency)

@app.route('/portfolio/<int:portfolio_id>/add_investment', methods=['GET', 'POST'])
def add_investment(portfolio_id):
    """Add investment to portfolio route"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    
    if request.method == 'POST':
        symbol = request.form.get('symbol')
        isin = request.form.get('isin')
        currency = request.form.get('currency') or 'USD'
        investment_type = request.form.get('type')
        quantity = float(request.form.get('quantity'))
        purchase_price = float(request.form.get('purchase_price'))
        purchase_date = datetime.strptime(request.form.get('purchase_date'), '%Y-%m-%d')
        # Prevent adding duplicate ISINs within the same portfolio
        existing = Investment.query.filter_by(portfolio_id=portfolio_id, isin=isin).first()
        if existing:
            flash('An investment with this ISIN already exists in the portfolio.', 'warning')
            return redirect(url_for('view_portfolio', portfolio_id=portfolio_id))

        investment = Investment(
            portfolio_id=portfolio_id,
            symbol=symbol,
            isin=isin,
            currency=currency,
            type=investment_type,
            quantity=quantity,
            purchase_price=purchase_price,
            purchase_date=purchase_date
        )
        
        db.session.add(investment)
        db.session.commit()
        
        flash('Investment added successfully!', 'success')
        return redirect(url_for('view_portfolio', portfolio_id=portfolio_id))
    
    return render_template('investment_form.html', portfolio=portfolio)

@app.route('/portfolio/<int:portfolio_id>/investment/<int:investment_id>/delete', methods=['POST'])
def delete_investment(portfolio_id, investment_id):
    """Delete an investment from a portfolio"""
    investment = Investment.query.get_or_404(investment_id)
    
    # Verify investment belongs to the specified portfolio
    if investment.portfolio_id != portfolio_id:
        flash('Invalid investment or portfolio.', 'error')
        return redirect(url_for('index'))
    
    db.session.delete(investment)
    db.session.commit()
    
    flash('Investment deleted successfully.', 'success')
    return redirect(url_for('view_portfolio', portfolio_id=portfolio_id))

@app.route('/portfolio/<int:portfolio_id>/delete', methods=['POST'])
def delete_portfolio(portfolio_id):
    """Delete a portfolio and all its investments"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    
    # SQLAlchemy will handle cascading delete of investments
    db.session.delete(portfolio)
    db.session.commit()
    
    flash('Portfolio and all its investments deleted successfully.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)