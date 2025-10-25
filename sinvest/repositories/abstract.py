from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
from sinvest.domain.entities import PortfolioEntity, InvestmentEntity


class PortfolioRepository(ABC):
    @abstractmethod
    def list_portfolios(self) -> List[PortfolioEntity]:
        raise NotImplementedError()

    @abstractmethod
    def get_portfolio(self, portfolio_id: int) -> PortfolioEntity | None:
        raise NotImplementedError()

    @abstractmethod
    def add_portfolio(self, name: str, description: str | None) -> PortfolioEntity:
        raise NotImplementedError()

    @abstractmethod
    def add_investment(self, investment: InvestmentEntity) -> InvestmentEntity:
        raise NotImplementedError()

    @abstractmethod
    def delete_investment(self, investment_id: int) -> None:
        raise NotImplementedError()

    @abstractmethod
    def delete_portfolio(self, portfolio_id: int) -> None:
        raise NotImplementedError()
