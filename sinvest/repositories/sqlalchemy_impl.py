"""SQLAlchemy-based repository implementation mapping persistence models to domain entities."""
from typing import List
from sinvest.repositories.abstract import PortfolioRepository
from sinvest.domain.entities import PortfolioEntity, InvestmentEntity
from sinvest.models.portfolio import Portfolio as PortfolioModel, Investment as InvestmentModel
from sinvest.app import db
from datetime import datetime


class SQLAlchemyPortfolioRepository(PortfolioRepository):
    def list_portfolios(self) -> List[PortfolioEntity]:
        models = PortfolioModel.query.all()
        return [self._to_entity(m) for m in models]

    def get_portfolio(self, portfolio_id: int) -> PortfolioEntity | None:
        m = db.session.get(PortfolioModel, portfolio_id)
        return self._to_entity(m) if m else None

    def add_portfolio(self, name: str, description: str | None) -> PortfolioEntity:
        m = PortfolioModel(name=name, description=description)
        db.session.add(m)
        db.session.commit()
        return self._to_entity(m)

    def add_investment(self, investment: InvestmentEntity) -> InvestmentEntity:
        im = InvestmentModel(
            portfolio_id=investment.portfolio_id,
            symbol=investment.symbol,
            isin=investment.isin,
            currency=investment.currency,
            type=investment.type,
            quantity=investment.quantity,
            purchase_price=investment.purchase_price,
            purchase_date=investment.purchase_date,
        )
        db.session.add(im)
        db.session.commit()
        return self._to_inv_entity(im)

    def delete_investment(self, investment_id: int) -> None:
        im = db.session.get(InvestmentModel, investment_id)
        if im:
            db.session.delete(im)
            db.session.commit()

    def delete_portfolio(self, portfolio_id: int) -> None:
        p = db.session.get(PortfolioModel, portfolio_id)
        if p:
            db.session.delete(p)
            db.session.commit()

    def _to_entity(self, m: PortfolioModel) -> PortfolioEntity:
        invs = [self._to_inv_entity(i) for i in (m.investments or [])]
        return PortfolioEntity(id=m.id, name=m.name, description=m.description, created_at=m.created_at, investments=invs)

    def _to_inv_entity(self, im: InvestmentModel) -> InvestmentEntity:
        return InvestmentEntity(
            id=im.id,
            portfolio_id=im.portfolio_id,
            symbol=im.symbol,
            isin=im.isin,
            currency=getattr(im, 'currency', 'USD'),
            type=im.type,
            quantity=im.quantity,
            purchase_price=im.purchase_price,
            purchase_date=im.purchase_date,
        )
