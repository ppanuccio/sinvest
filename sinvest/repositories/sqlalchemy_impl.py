"""SQLAlchemy-based repository implementation mapping persistence models to domain entities."""
from typing import List
from sinvest.repositories.abstract import PortfolioRepository
from sinvest.domain.entities import PortfolioEntity, InvestmentEntity, TransactionEntity
from sinvest.models.portfolio import Portfolio as PortfolioModel, Investment as InvestmentModel, Transaction as TransactionModel
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
        # If the InvestmentEntity includes an initial transaction list, persist them
        if getattr(investment, 'transactions', None):
            for tx in investment.transactions:
                tm = TransactionModel(
                    investment_id=im.id,
                    quantity=tx.quantity,
                    unit_price=tx.unit_price,
                    transaction_date=tx.transaction_date,
                )
                db.session.add(tm)
            db.session.commit()
        return self._to_inv_entity(im)

    def add_transaction(self, portfolio_id: int, isin: str, quantity: float, unit_price: float, transaction_date) -> TransactionEntity:
        # Find the investment by portfolio_id + isin (should be unique)
        im = db.session.execute(
            db.select(InvestmentModel).where(InvestmentModel.portfolio_id == portfolio_id, InvestmentModel.isin == isin)
        ).scalars().first()
        if not im:
            raise ValueError("Investment not found for portfolio and ISIN")
        tm = TransactionModel(
            investment_id=im.id,
            quantity=quantity,
            unit_price=unit_price,
            transaction_date=transaction_date,
        )
        db.session.add(tm)
        db.session.commit()
        return TransactionEntity(id=tm.id, investment_id=tm.investment_id, quantity=tm.quantity, unit_price=tm.unit_price, transaction_date=tm.transaction_date, created_at=tm.created_at)

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
        # Map transactions if present
        txs = []
        for t in (getattr(im, 'transactions', []) or []):
            txs.append(TransactionEntity(id=t.id, investment_id=t.investment_id, quantity=t.quantity, unit_price=t.unit_price, transaction_date=t.transaction_date, created_at=t.created_at))

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
            transactions=txs,
        )
