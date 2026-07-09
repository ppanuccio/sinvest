"""In-memory repository implementations for CLI infrastructure."""

from datetime import datetime
from typing import Dict, List, Optional

from app.domain.entities.auth import UserCredential
from app.domain.entities.user import User
from app.domain.entities.portfolio import Portfolio
from app.domain.entities.investment import Investment
from app.domain.entities.transaction import Transaction
from app.domain.entities.price_history import PriceHistory
from app.domain.repositories.credential_repository import CredentialRepository
from app.domain.repositories.user_repository import UserRepository
from app.domain.repositories.portfolio_repository import PortfolioRepository
from app.domain.repositories.investment_repository import InvestmentRepository
from app.domain.repositories.transaction_repository import TransactionRepository
from app.domain.repositories.price_history_repository import (
    PriceHistoryRepository,
)


class InMemoryUserRepository(UserRepository):
    """In-memory implementation of UserRepository."""

    def __init__(self):
        self._users: Dict[str, User] = {}

    def save(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def exists_by_username(self, username: str) -> bool:
        return self.get_by_username(username) is not None

    def list_all(self) -> List[User]:
        return list(self._users.values())

    def delete(self, user_id: str) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False

    def update(self, user: User) -> User:
        self._users[user.id] = user
        return user


class InMemoryCredentialRepository(CredentialRepository):
    """In-memory implementation of CredentialRepository."""

    def __init__(self):
        self._credentials: Dict[str, UserCredential] = {}

    def save(self, credential: UserCredential) -> UserCredential:
        self._credentials[credential.user_id] = credential
        return credential

    def get_by_username(self, username: str) -> Optional[UserCredential]:
        for credential in self._credentials.values():
            if credential.username == username:
                return credential
        return None

    def get_by_user_id(self, user_id: str) -> Optional[UserCredential]:
        return self._credentials.get(user_id)

    def delete_by_user_id(self, user_id: str) -> bool:
        if user_id not in self._credentials:
            return False
        del self._credentials[user_id]
        return True


class InMemoryPortfolioRepository(PortfolioRepository):
    """In-memory implementation of PortfolioRepository."""

    def __init__(self):
        self._portfolios: Dict[str, Portfolio] = {}

    def save(self, portfolio: Portfolio) -> Portfolio:
        self._portfolios[portfolio.id] = portfolio
        return portfolio

    def get_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        return self._portfolios.get(portfolio_id)

    def list_by_user(self, user_id: str) -> List[Portfolio]:
        return [
            p for p in self._portfolios.values() if p.user_id == user_id
        ]

    def update(self, portfolio: Portfolio) -> Portfolio:
        self._portfolios[portfolio.id] = portfolio
        return portfolio

    def delete(self, portfolio_id: str) -> bool:
        if portfolio_id in self._portfolios:
            del self._portfolios[portfolio_id]
            return True
        return False

    def exists(self, portfolio_id: str) -> bool:
        return portfolio_id in self._portfolios


class InMemoryInvestmentRepository(InvestmentRepository):
    """In-memory implementation of InvestmentRepository."""

    def __init__(self):
        self._investments: Dict[str, Investment] = {}

    def save(self, investment: Investment) -> Investment:
        self._investments[investment.id] = investment
        return investment

    def get_by_id(self, investment_id: str) -> Optional[Investment]:
        return self._investments.get(investment_id)

    def list_by_portfolio(self, portfolio_id: str) -> List[Investment]:
        return [
            i
            for i in self._investments.values()
            if i.portfolio_id == portfolio_id
        ]

    def update(self, investment: Investment) -> Investment:
        self._investments[investment.id] = investment
        return investment

    def delete(self, investment_id: str) -> bool:
        if investment_id in self._investments:
            del self._investments[investment_id]
            return True
        return False

    def exists(self, investment_id: str) -> bool:
        return investment_id in self._investments


class InMemoryTransactionRepository(TransactionRepository):
    """In-memory implementation of TransactionRepository."""

    def __init__(self):
        self._transactions: Dict[str, Transaction] = {}

    def save(self, transaction: Transaction) -> Transaction:
        self._transactions[transaction.id] = transaction
        return transaction

    def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        return self._transactions.get(transaction_id)

    def list_by_investment(self, investment_id: str) -> List[Transaction]:
        txns = [
            t
            for t in self._transactions.values()
            if t.investment_id == investment_id
        ]
        return sorted(txns, key=lambda t: t.date)

    def update(self, transaction: Transaction) -> Transaction:
        self._transactions[transaction.id] = transaction
        return transaction

    def delete(self, transaction_id: str) -> bool:
        if transaction_id in self._transactions:
            del self._transactions[transaction_id]
            return True
        return False

    def exists(self, transaction_id: str) -> bool:
        return transaction_id in self._transactions

    def delete_by_investment(self, investment_id: str) -> int:
        to_delete = [
            t_id
            for t_id, t in self._transactions.items()
            if t.investment_id == investment_id
        ]
        for t_id in to_delete:
            del self._transactions[t_id]
        return len(to_delete)


class InMemoryPriceHistoryRepository(PriceHistoryRepository):
    """In-memory implementation of PriceHistoryRepository."""

    def __init__(self):
        self._prices: Dict[str, PriceHistory] = {}

    def save(self, price_history: PriceHistory) -> PriceHistory:
        self._prices[price_history.id] = price_history
        return price_history

    def get_by_id(self, price_history_id: str) -> Optional[PriceHistory]:
        return self._prices.get(price_history_id)

    def get_latest_price(self, investment_id: str) -> Optional[PriceHistory]:
        prices = self.list_by_investment(investment_id)
        return prices[0] if prices else None

    def list_by_investment(self, investment_id: str) -> List[PriceHistory]:
        prices = [
            p
            for p in self._prices.values()
            if p.investment_id == investment_id
        ]
        return sorted(prices, key=lambda p: p.date, reverse=True)

    def list_by_investment_and_date_range(
        self,
        investment_id: str,
        from_date: datetime,
        to_date: datetime,
    ) -> List[PriceHistory]:
        prices = [
            p
            for p in self._prices.values()
            if p.investment_id == investment_id
            and from_date <= p.date <= to_date
        ]
        return sorted(prices, key=lambda p: p.date, reverse=True)

    def delete(self, price_history_id: str) -> bool:
        if price_history_id in self._prices:
            del self._prices[price_history_id]
            return True
        return False

    def delete_by_investment(self, investment_id: str) -> int:
        to_delete = [
            p_id
            for p_id, p in self._prices.items()
            if p.investment_id == investment_id
        ]
        for p_id in to_delete:
            del self._prices[p_id]
        return len(to_delete)
