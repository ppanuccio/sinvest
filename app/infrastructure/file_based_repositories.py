"""File-based repository implementations for persistent CLI infrastructure."""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.domain.entities.auth import UserCredential
from app.domain.entities.investment import Investment
from app.domain.entities.portfolio import Portfolio
from app.domain.entities.price_history import PriceHistory
from app.domain.entities.transaction import Transaction
from app.domain.entities.user import User
from app.domain.repositories.credential_repository import CredentialRepository
from app.domain.repositories.investment_repository import InvestmentRepository
from app.domain.repositories.portfolio_repository import PortfolioRepository
from app.domain.repositories.price_history_repository import (
    PriceHistoryRepository,
)
from app.domain.repositories.transaction_repository import TransactionRepository
from app.domain.repositories.user_repository import UserRepository
from app.domain.value_objects import Identifier, InvestmentType, Money, Quantity


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for domain types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Identifier):
            return {
                "__identifier__": True,
                "value": obj.value,
                "identifier_type": obj.identifier_type,
            }
        if isinstance(obj, InvestmentType):
            return obj.value
        if isinstance(obj, Money):
            return {
                "__money__": True,
                "amount": str(obj.amount),
                "currency": obj.currency,
            }
        if isinstance(obj, Quantity):
            return {
                "__quantity__": True,
                "value": str(obj.value),
            }
        return super().default(obj)


def _decode_value(obj: Any) -> Any:
    """Decode custom types from JSON."""
    if isinstance(obj, dict):
        if obj.get("__identifier__"):
            return Identifier(
                value=obj["value"],
                identifier_type=obj["identifier_type"],
            )
        if obj.get("__money__"):
            return Money(
                amount=Decimal(obj["amount"]),
                currency=obj["currency"],
            )
        if obj.get("__quantity__"):
            return Quantity(value=Decimal(obj["value"]))
    if isinstance(obj, str):
        try:
            return datetime.fromisoformat(obj)
        except (ValueError, TypeError):
            return obj
    return obj


class FileBasedUserRepository(UserRepository):
    """File-based implementation of UserRepository."""

    def __init__(self, file_path: str = "data/users.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("[]")

    def _load(self) -> Dict[str, dict]:
        with open(self.file_path, "r") as f:
            users = json.load(f)
        return {u["id"]: u for u in users}

    def _save(self, users: Dict[str, dict]) -> None:
        with open(self.file_path, "w") as f:
            json.dump(list(users.values()), f, cls=JSONEncoder, indent=2)

    def save(self, user: User) -> User:
        users = self._load()
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        users[user.id] = user_data
        self._save(users)
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        users = self._load()
        if user_id not in users:
            return None
        u = users[user_id]
        return User(
            id=u["id"],
            username=u["username"],
            email=u["email"],
            created_at=_decode_value(u["created_at"]),
            updated_at=_decode_value(u.get("updated_at")),
        )

    def get_by_username(self, username: str) -> Optional[User]:
        users = self._load()
        for u in users.values():
            if u["username"] == username:
                return User(
                    id=u["id"],
                    username=u["username"],
                    email=u["email"],
                    created_at=_decode_value(u["created_at"]),
                    updated_at=_decode_value(u.get("updated_at")),
                )
        return None

    def exists_by_username(self, username: str) -> bool:
        return self.get_by_username(username) is not None

    def list_all(self) -> List[User]:
        users = self._load()
        return [
            User(
                id=u["id"],
                username=u["username"],
                email=u["email"],
                created_at=_decode_value(u["created_at"]),
                updated_at=_decode_value(u.get("updated_at")),
            )
            for u in users.values()
        ]

    def delete(self, user_id: str) -> bool:
        users = self._load()
        if user_id not in users:
            return False
        del users[user_id]
        self._save(users)
        return True

    def update(self, user: User) -> User:
        return self.save(user)


class FileBasedCredentialRepository(CredentialRepository):
    """File-based implementation of CredentialRepository."""

    def __init__(self, file_path: str = "data/credentials.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("[]")

    def _load(self) -> Dict[str, dict]:
        with open(self.file_path, "r") as f:
            credentials = json.load(f)
        return {credential["user_id"]: credential for credential in credentials}

    def _save(self, credentials: Dict[str, dict]) -> None:
        with open(self.file_path, "w") as f:
            json.dump(
                list(credentials.values()),
                f,
                cls=JSONEncoder,
                indent=2,
            )

    def save(self, credential: UserCredential) -> UserCredential:
        credentials = self._load()
        credentials[credential.user_id] = {
            "user_id": credential.user_id,
            "username": credential.username,
            "password_hash": credential.password_hash,
            "created_at": credential.created_at,
            "updated_at": credential.updated_at,
        }
        self._save(credentials)
        return credential

    def get_by_username(self, username: str) -> Optional[UserCredential]:
        credentials = self._load()
        for credential in credentials.values():
            if credential["username"] == username:
                return self._to_entity(credential)
        return None

    def get_by_user_id(self, user_id: str) -> Optional[UserCredential]:
        credentials = self._load()
        credential = credentials.get(user_id)
        return self._to_entity(credential) if credential else None

    def delete_by_user_id(self, user_id: str) -> bool:
        credentials = self._load()
        if user_id not in credentials:
            return False
        del credentials[user_id]
        self._save(credentials)
        return True

    def _to_entity(self, credential: dict) -> UserCredential:
        return UserCredential(
            user_id=credential["user_id"],
            username=credential["username"],
            password_hash=credential["password_hash"],
            created_at=_decode_value(credential["created_at"]),
            updated_at=_decode_value(credential.get("updated_at")),
        )


class FileBasedPortfolioRepository(PortfolioRepository):
    """File-based implementation of PortfolioRepository."""

    def __init__(self, file_path: str = "data/portfolios.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("[]")

    def _load(self) -> Dict[str, dict]:
        with open(self.file_path, "r") as f:
            portfolios = json.load(f)
        return {p["id"]: p for p in portfolios}

    def _save(self, portfolios: Dict[str, dict]) -> None:
        with open(self.file_path, "w") as f:
            json.dump(
                list(portfolios.values()),
                f,
                cls=JSONEncoder,
                indent=2,
            )

    def save(self, portfolio: Portfolio) -> Portfolio:
        portfolios = self._load()
        portfolio_data = {
            "id": portfolio.id,
            "user_id": portfolio.user_id,
            "name": portfolio.name,
            "description": portfolio.description,
            "created_at": portfolio.created_at,
            "updated_at": portfolio.updated_at,
        }
        portfolios[portfolio.id] = portfolio_data
        self._save(portfolios)
        return portfolio

    def get_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        portfolios = self._load()
        if portfolio_id not in portfolios:
            return None
        p = portfolios[portfolio_id]
        return Portfolio(
            id=p["id"],
            user_id=p["user_id"],
            name=p["name"],
            description=p.get("description"),
            created_at=_decode_value(p["created_at"]),
            updated_at=_decode_value(p.get("updated_at")),
        )

    def list_by_user(self, user_id: str) -> List[Portfolio]:
        portfolios = self._load()
        return [
            Portfolio(
                id=p["id"],
                user_id=p["user_id"],
                name=p["name"],
                description=p.get("description"),
                created_at=_decode_value(p["created_at"]),
                updated_at=_decode_value(p.get("updated_at")),
            )
            for p in portfolios.values()
            if p["user_id"] == user_id
        ]

    def update(self, portfolio: Portfolio) -> Portfolio:
        return self.save(portfolio)

    def delete(self, portfolio_id: str) -> bool:
        portfolios = self._load()
        if portfolio_id not in portfolios:
            return False
        del portfolios[portfolio_id]
        self._save(portfolios)
        return True

    def exists(self, portfolio_id: str) -> bool:
        portfolios = self._load()
        return portfolio_id in portfolios


class FileBasedInvestmentRepository(InvestmentRepository):
    """File-based implementation of InvestmentRepository."""

    def __init__(self, file_path: str = "data/investments.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("[]")

    def _load(self) -> Dict[str, dict]:
        with open(self.file_path, "r") as f:
            investments = json.load(f)
        return {i["id"]: i for i in investments}

    def _save(self, investments: Dict[str, dict]) -> None:
        with open(self.file_path, "w") as f:
            json.dump(
                list(investments.values()),
                f,
                cls=JSONEncoder,
                indent=2,
            )

    def save(self, investment: Investment) -> Investment:
        investments = self._load()
        investment_data = {
            "id": investment.id,
            "portfolio_id": investment.portfolio_id,
            "identifier": investment.identifier,
            "type": investment.type,
            "created_at": investment.created_at,
            "updated_at": investment.updated_at,
        }
        investments[investment.id] = investment_data
        self._save(investments)
        return investment

    def get_by_id(self, investment_id: str) -> Optional[Investment]:
        investments = self._load()
        if investment_id not in investments:
            return None
        i = investments[investment_id]
        identifier = _decode_value(i["identifier"])
        investment_type = _decode_value(i["type"])
        if isinstance(investment_type, str):
            investment_type = InvestmentType(investment_type)
        return Investment(
            id=i["id"],
            portfolio_id=i["portfolio_id"],
            identifier=identifier,
            type=investment_type,
            created_at=_decode_value(i["created_at"]),
            updated_at=_decode_value(i.get("updated_at")),
        )

    def list_by_portfolio(self, portfolio_id: str) -> List[Investment]:
        investments = self._load()
        result = []
        for i in investments.values():
            if i["portfolio_id"] == portfolio_id:
                identifier = _decode_value(i["identifier"])
                investment_type = _decode_value(i["type"])
                if isinstance(investment_type, str):
                    investment_type = InvestmentType(investment_type)
                result.append(
                    Investment(
                        id=i["id"],
                        portfolio_id=i["portfolio_id"],
                        identifier=identifier,
                        type=investment_type,
                        created_at=_decode_value(i["created_at"]),
                        updated_at=_decode_value(i.get("updated_at")),
                    )
                )
        return result

    def update(self, investment: Investment) -> Investment:
        return self.save(investment)

    def delete(self, investment_id: str) -> bool:
        investments = self._load()
        if investment_id not in investments:
            return False
        del investments[investment_id]
        self._save(investments)
        return True

    def exists(self, investment_id: str) -> bool:
        investments = self._load()
        return investment_id in investments


class FileBasedTransactionRepository(TransactionRepository):
    """File-based implementation of TransactionRepository."""

    def __init__(self, file_path: str = "data/transactions.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("[]")

    def _load(self) -> Dict[str, dict]:
        with open(self.file_path, "r") as f:
            transactions = json.load(f)
        return {t["id"]: t for t in transactions}

    def _save(self, transactions: Dict[str, dict]) -> None:
        with open(self.file_path, "w") as f:
            json.dump(
                list(transactions.values()),
                f,
                cls=JSONEncoder,
                indent=2,
            )

    def save(self, transaction: Transaction) -> Transaction:
        transactions = self._load()
        transaction_data = {
            "id": transaction.id,
            "investment_id": transaction.investment_id,
            "amount": transaction.amount,
            "quantity": transaction.quantity,
            "broker": transaction.broker,
            "date": transaction.date,
            "created_at": transaction.created_at,
            "updated_at": transaction.updated_at,
        }
        transactions[transaction.id] = transaction_data
        self._save(transactions)
        return transaction

    def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        transactions = self._load()
        if transaction_id not in transactions:
            return None
        t = transactions[transaction_id]
        return Transaction(
            id=t["id"],
            investment_id=t["investment_id"],
            amount=_decode_value(t["amount"]),
            quantity=_decode_value(t["quantity"]),
            broker=t["broker"],
            date=_decode_value(t["date"]),
            created_at=_decode_value(t["created_at"]),
            updated_at=_decode_value(t["updated_at"]),
        )

    def list_by_investment(self, investment_id: str) -> List[Transaction]:
        transactions = self._load()
        result = []
        for t in transactions.values():
            if t["investment_id"] == investment_id:
                result.append(
                    Transaction(
                        id=t["id"],
                        investment_id=t["investment_id"],
                        amount=_decode_value(t["amount"]),
                        quantity=_decode_value(t["quantity"]),
                        broker=t["broker"],
                        date=_decode_value(t["date"]),
                        created_at=_decode_value(t["created_at"]),
                        updated_at=_decode_value(t["updated_at"]),
                    )
                )
        return sorted(result, key=lambda tx: tx.date)

    def update(self, transaction: Transaction) -> Transaction:
        return self.save(transaction)

    def delete(self, transaction_id: str) -> bool:
        transactions = self._load()
        if transaction_id not in transactions:
            return False
        del transactions[transaction_id]
        self._save(transactions)
        return True

    def exists(self, transaction_id: str) -> bool:
        transactions = self._load()
        return transaction_id in transactions

    def delete_by_investment(self, investment_id: str) -> int:
        transactions = self._load()
        to_delete = [
            t_id
            for t_id, t in transactions.items()
            if t["investment_id"] == investment_id
        ]
        for t_id in to_delete:
            del transactions[t_id]
        self._save(transactions)
        return len(to_delete)


class FileBasedPriceHistoryRepository(PriceHistoryRepository):
    """File-based implementation of PriceHistoryRepository."""

    def __init__(self, file_path: str = "data/price_history.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("[]")

    def _load(self) -> Dict[str, dict]:
        with open(self.file_path, "r") as f:
            prices = json.load(f)
        return {p["id"]: p for p in prices}

    def _save(self, prices: Dict[str, dict]) -> None:
        with open(self.file_path, "w") as f:
            json.dump(
                list(prices.values()),
                f,
                cls=JSONEncoder,
                indent=2,
            )

    def save(self, price_history: PriceHistory) -> PriceHistory:
        prices = self._load()
        price_data = {
            "id": price_history.id,
            "investment_id": price_history.investment_id,
            "price": price_history.price,
            "date": price_history.date,
            "created_at": price_history.created_at,
        }
        prices[price_history.id] = price_data
        self._save(prices)
        return price_history

    def get_by_id(self, price_history_id: str) -> Optional[PriceHistory]:
        prices = self._load()
        if price_history_id not in prices:
            return None
        p = prices[price_history_id]
        return PriceHistory(
            id=p["id"],
            investment_id=p["investment_id"],
            price=_decode_value(p["price"]),
            date=_decode_value(p["date"]),
            created_at=_decode_value(p["created_at"]),
        )

    def get_latest_price(self, investment_id: str) -> Optional[PriceHistory]:
        prices = self.list_by_investment(investment_id)
        return prices[0] if prices else None

    def list_by_investment(self, investment_id: str) -> List[PriceHistory]:
        prices = self._load()
        result = []
        for p in prices.values():
            if p["investment_id"] == investment_id:
                result.append(
                    PriceHistory(
                        id=p["id"],
                        investment_id=p["investment_id"],
                        price=_decode_value(p["price"]),
                        date=_decode_value(p["date"]),
                        created_at=_decode_value(p["created_at"]),
                    )
                )
        return sorted(result, key=lambda ph: ph.date, reverse=True)

    def list_by_investment_and_date_range(
        self,
        investment_id: str,
        from_date: datetime,
        to_date: datetime,
    ) -> List[PriceHistory]:
        prices = self._load()
        result = []
        for p in prices.values():
            p_date = _decode_value(p["date"])
            if (
                p["investment_id"] == investment_id
                and from_date <= p_date <= to_date
            ):
                result.append(
                    PriceHistory(
                        id=p["id"],
                        investment_id=p["investment_id"],
                        price=_decode_value(p["price"]),
                        date=p_date,
                        created_at=_decode_value(p["created_at"]),
                    )
                )
        return sorted(result, key=lambda ph: ph.date, reverse=True)

    def delete(self, price_history_id: str) -> bool:
        prices = self._load()
        if price_history_id not in prices:
            return False
        del prices[price_history_id]
        self._save(prices)
        return True

    def delete_by_investment(self, investment_id: str) -> int:
        prices = self._load()
        to_delete = [
            p_id
            for p_id, p in prices.items()
            if p["investment_id"] == investment_id
        ]
        for p_id in to_delete:
            del prices[p_id]
        self._save(prices)
        return len(to_delete)
