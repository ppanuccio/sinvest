"""Price History use cases - orchestrates price tracking operations."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from app.domain.entities.price_history import PriceHistory
from app.domain.repositories.price_history_repository import PriceHistoryRepository
from app.domain.repositories.investment_repository import InvestmentRepository
from app.domain.repositories.portfolio_repository import PortfolioRepository
from app.domain.value_objects import Money
from app.domain.services.validation_service import ValidationService
from app.domain.exceptions import (
    EntityNotFoundException,
    UnauthorizedException,
)
from app.application.dto.price_history_dto import (
    CreatePriceHistoryDTO,
    PriceHistoryResponseDTO,
)


class PriceHistoryUseCases:
    """Orchestrates all price history operations."""

    def __init__(
        self,
        price_history_repository: PriceHistoryRepository,
        investment_repository: InvestmentRepository,
        portfolio_repository: PortfolioRepository,
    ):
        self.price_history_repository = price_history_repository
        self.investment_repository = investment_repository
        self.portfolio_repository = portfolio_repository
        self.validation_service = ValidationService()

    def record_price(
        self, user_id: str, dto: CreatePriceHistoryDTO
    ) -> PriceHistoryResponseDTO:
        """Record a new price for an investment."""
        # Verify investment exists and belongs to user
        investment = self.investment_repository.get_by_id(dto.investment_id)
        if not investment:
            raise EntityNotFoundException("Investment", dto.investment_id)

        portfolio = self.portfolio_repository.get_by_id(
            investment.portfolio_id
        )
        if not portfolio or portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own investment {dto.investment_id}"
            )

        # Validate price data
        self.validation_service.validate_price_is_positive(dto.price)
        self.validation_service.validate_price_date(dto.date)

        # Create price history entity
        price_history = PriceHistory(
            id=str(uuid.uuid4()),
            investment_id=dto.investment_id,
            price=Money(dto.price, "USD"),
            date=dto.date,
            created_at=datetime.utcnow(),
        )

        # Save and return
        saved = self.price_history_repository.save(price_history)
        return self._to_response_dto(saved)

    def get_latest_price(
        self, investment_id: str, user_id: str
    ) -> Optional[PriceHistoryResponseDTO]:
        """Get the most recent price for an investment."""
        # Verify investment exists and belongs to user
        investment = self.investment_repository.get_by_id(investment_id)
        if not investment:
            raise EntityNotFoundException("Investment", investment_id)

        portfolio = self.portfolio_repository.get_by_id(
            investment.portfolio_id
        )
        if not portfolio or portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own investment {investment_id}"
            )

        price_history = self.price_history_repository.get_latest_price(
            investment_id
        )
        if not price_history:
            return None

        return self._to_response_dto(price_history)

    def list_prices(
        self, investment_id: str, user_id: str
    ) -> List[PriceHistoryResponseDTO]:
        """List all prices for an investment."""
        # Verify investment exists and belongs to user
        investment = self.investment_repository.get_by_id(investment_id)
        if not investment:
            raise EntityNotFoundException("Investment", investment_id)

        portfolio = self.portfolio_repository.get_by_id(
            investment.portfolio_id
        )
        if not portfolio or portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own investment {investment_id}"
            )

        prices = self.price_history_repository.list_by_investment(
            investment_id
        )
        return [self._to_response_dto(p) for p in prices]

    def list_prices_by_date_range(
        self,
        investment_id: str,
        user_id: str,
        from_date: datetime,
        to_date: datetime,
    ) -> List[PriceHistoryResponseDTO]:
        """List prices within a date range."""
        # Verify investment exists and belongs to user
        investment = self.investment_repository.get_by_id(investment_id)
        if not investment:
            raise EntityNotFoundException("Investment", investment_id)

        portfolio = self.portfolio_repository.get_by_id(
            investment.portfolio_id
        )
        if not portfolio or portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own investment {investment_id}"
            )

        prices = self.price_history_repository.list_by_investment_and_date_range(
            investment_id, from_date, to_date
        )
        return [self._to_response_dto(p) for p in prices]

    def _to_response_dto(
        self, price_history: PriceHistory
    ) -> PriceHistoryResponseDTO:
        """Convert price history entity to response DTO."""
        return PriceHistoryResponseDTO(
            id=price_history.id,
            investment_id=price_history.investment_id,
            price=price_history.price.amount,
            date=price_history.date,
            created_at=price_history.created_at,
        )
