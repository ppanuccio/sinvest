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


@dataclass
class PortfolioEntity:
    id: int | None
    name: str
    description: str | None
    created_at: datetime | None
    investments: List[InvestmentEntity]
