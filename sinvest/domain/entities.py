from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class InvestmentEntity:
    id: int | None
    portfolio_id: int
    symbol: str
    isin: str
    currency: str
    type: str
    quantity: float
    purchase_price: float
    purchase_date: datetime
    transactions: List["TransactionEntity"] | None = None


@dataclass
class PortfolioEntity:
    id: int | None
    name: str
    description: str | None
    created_at: datetime | None
    investments: List[InvestmentEntity]



@dataclass
class TransactionEntity:
    id: int | None
    investment_id: int
    quantity: float
    unit_price: float
    transaction_date: datetime
    created_at: datetime | None = None
