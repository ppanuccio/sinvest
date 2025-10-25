"""Portfolio and Investment models"""
from datetime import datetime
import yfinance as yf
from sinvest.app import db

class Portfolio(db.Model):
    """Portfolio model representing an investment portfolio"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    investments = db.relationship('Investment', backref='portfolio', lazy=True, cascade='all, delete-orphan')

    def get_total_value(self):
        """Return total current values grouped by currency.

        Returns:
            dict: { 'USD': 1234.56, 'EUR': 789.01 }
        """
        totals = {}
        for inv in self.investments:
            cur = getattr(inv, 'currency', 'USD') or 'USD'
            totals[cur] = totals.get(cur, 0.0) + (inv.get_current_value() or 0.0)
        return totals

    def get_total_gain_loss(self):
        """Return total gain/loss grouped by currency.

        Returns:
            dict: { 'USD': 123.45, 'EUR': -67.89 }
        """
        gains = {}
        for inv in self.investments:
            cur = getattr(inv, 'currency', 'USD') or 'USD'
            gains[cur] = gains.get(cur, 0.0) + (inv.get_gain_loss() or 0.0)
        return gains

class Investment(db.Model):
    """Investment model representing individual investments in a portfolio"""
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    isin = db.Column(db.String(12), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    type = db.Column(db.String(20), nullable=False)  # 'equity', 'bond', 'etf'
    quantity = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Ensure the same ISIN cannot be added multiple times to the same portfolio.
    # (We keep this at the model level; applying it to an existing SQLite DB
    # requires a migration. We also add a runtime check when creating records.)
    __table_args__ = (db.UniqueConstraint('portfolio_id', 'isin', name='uix_portfolio_isin'),)

    def get_current_price(self):
        """Get current price of the investment using yfinance"""
        try:
            ticker = yf.Ticker(self.symbol)
            return ticker.history(period='1d')['Close'].iloc[-1]
        except:
            return self.purchase_price  # Fallback to purchase price if unable to fetch

    def get_current_value(self):
        """Calculate current value of the investment in the investment's currency.

        This function assumes the fetched price and the stored purchase price
        are expressed in the same currency as `self.currency`.
        """
        price = self.get_current_price() or 0.0
        return self.quantity * price

    def get_gain_loss(self):
        """Calculate total gain/loss for the investment in the investment's currency."""
        current_value = self.get_current_value() or 0.0
        initial_value = (self.quantity or 0.0) * (self.purchase_price or 0.0)
        return current_value - initial_value