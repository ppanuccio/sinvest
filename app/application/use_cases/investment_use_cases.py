"""Investment use cases - orchestrates investment operations."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List

from app.domain.entities.investment import Investment
from app.domain.repositories.investment_repository import InvestmentRepository
from app.domain.repositories.portfolio_repository import PortfolioRepository
from app.domain.repositories.transaction_repository import TransactionRepository
from app.domain.repositories.price_history_repository import (
    PriceHistoryRepository,
)
from app.domain.value_objects import Identifier, InvestmentType, Money
from app.domain.services.validation_service import ValidationService
from app.domain.exceptions import (
    EntityNotFoundException,
    UnauthorizedException,
    InvalidInvestmentException,
)
from app.application.dto.investment_dto import (
    CreateInvestmentDTO,
    UpdateInvestmentDTO,
    InvestmentResponseDTO,
)


class InvestmentUseCases:
    """Orchestrates all investment-related operations."""

    def __init__(
        self,
        investment_repository: InvestmentRepository,
        portfolio_repository: PortfolioRepository,
        transaction_repository: TransactionRepository | None = None,
        price_history_repository: PriceHistoryRepository | None = None,
    ):
        self.investment_repository = investment_repository
        self.portfolio_repository = portfolio_repository
        self.transaction_repository = transaction_repository
        self.price_history_repository = price_history_repository
        self.validation_service = ValidationService()

    def create_investment(
        self, user_id: str, dto: CreateInvestmentDTO
    ) -> InvestmentResponseDTO:
        """Create a new investment in a portfolio."""
        # Verify portfolio exists and belongs to user
        portfolio = self.portfolio_repository.get_by_id(dto.portfolio_id)
        if not portfolio:
            raise EntityNotFoundException("Portfolio", dto.portfolio_id)

        if portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own portfolio {dto.portfolio_id}"
            )

        # Validate identifier format
        self.validation_service.validate_identifier_format(
            dto.identifier, dto.identifier_type
        )

        # Create identifier value object
        if dto.identifier_type.upper() == "ISIN":
            identifier = Identifier.create_isin(dto.identifier)
        else:
            identifier = Identifier.create_ticker(dto.identifier)

        # Validate and convert investment type
        investment_type = self.validation_service.validate_investment_type(
            dto.type
        )

        # Build face value (bond nominal per unit) as a Money value object.
        # Explicit currency avoids the Money default-currency ("EUR") gotcha.
        face_value = None
        if dto.face_value is not None:
            if dto.face_value <= 0:
                raise InvalidInvestmentException("face_value must be positive")
            face_value = Money(
                Decimal(str(dto.face_value)), dto.face_value_currency or "USD"
            )

        # A held-to-maturity bond is valued on its face value basis; without a
        # face value it would silently degrade to the market-price path.
        if dto.held_to_maturity and face_value is None:
            raise InvalidInvestmentException(
                "held_to_maturity requires a face_value"
            )

        # Create investment entity
        investment = Investment(
            id=str(uuid.uuid4()),
            portfolio_id=dto.portfolio_id,
            identifier=identifier,
            type=investment_type,
            created_at=datetime.utcnow(),
            held_to_maturity=dto.held_to_maturity,
            face_value=face_value,
            name=dto.name,
        )

        # Save and return
        saved = self.investment_repository.save(investment)
        return self._to_response_dto(saved)

    def get_investment(
        self, investment_id: str, user_id: str
    ) -> InvestmentResponseDTO:
        """Get an investment by ID with authorization check."""
        investment = self.investment_repository.get_by_id(investment_id)
        if not investment:
            raise EntityNotFoundException("Investment", investment_id)

        # Verify user owns the portfolio containing this investment
        portfolio = self.portfolio_repository.get_by_id(
            investment.portfolio_id
        )
        if not portfolio or portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own investment {investment_id}"
            )

        return self._to_response_dto(investment)

    def list_investments(
        self, portfolio_id: str, user_id: str
    ) -> List[InvestmentResponseDTO]:
        """List all investments in a portfolio."""
        # Verify portfolio exists and belongs to user
        portfolio = self.portfolio_repository.get_by_id(portfolio_id)
        if not portfolio:
            raise EntityNotFoundException("Portfolio", portfolio_id)

        if portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own portfolio {portfolio_id}"
            )

        investments = self.investment_repository.list_by_portfolio(
            portfolio_id
        )
        return [self._to_response_dto(inv) for inv in investments]

    def update_investment(
        self, investment_id: str, user_id: str, dto: UpdateInvestmentDTO
    ) -> InvestmentResponseDTO:
        """Update an investment."""
        # Get and verify ownership
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

        # Validate input if provided
        face_value = None
        if dto.face_value is not None:
            if dto.face_value <= 0:
                raise InvalidInvestmentException("face_value must be positive")
            currency = dto.face_value_currency or "USD"
            face_value = Money(Decimal(str(dto.face_value)), currency)

        # A held-to-maturity bond must keep a face value: enforce the invariant
        # on the effective post-update state.
        effective_htm = (
            dto.held_to_maturity
            if dto.held_to_maturity is not None
            else investment.held_to_maturity
        )
        effective_face = (
            face_value if face_value is not None else investment.face_value
        )
        if effective_htm and effective_face is None:
            raise InvalidInvestmentException(
                "held_to_maturity requires a face_value"
            )

        if any(
            value is not None
            for value in (dto.type, dto.held_to_maturity, dto.face_value, dto.name)
        ):
            investment_type = None
            if dto.type:
                investment_type = self.validation_service.validate_investment_type(
                    dto.type
                )
            investment.update_details(
                type=investment_type,
                held_to_maturity=dto.held_to_maturity,
                face_value=face_value,
                name=dto.name,
                updated_at=datetime.utcnow(),
            )
            updated = self.investment_repository.update(investment)
            return self._to_response_dto(updated)

        return self._to_response_dto(investment)

    def delete_investment(self, investment_id: str, user_id: str) -> None:
        """Delete an investment and its related transactions and price history."""
        # Get and verify ownership
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

        # Clean up related data
        if self.transaction_repository:
            self.transaction_repository.delete_by_investment(investment_id)
        if self.price_history_repository:
            self.price_history_repository.delete_by_investment(investment_id)

        # Delete the investment
        self.investment_repository.delete(investment_id)

    def _to_response_dto(self, investment: Investment) -> InvestmentResponseDTO:
        """Convert investment entity to response DTO."""
        return InvestmentResponseDTO(
            id=investment.id,
            portfolio_id=investment.portfolio_id,
            identifier=investment.identifier.value,
            identifier_type=investment.identifier.identifier_type,
            type=investment.type.value,
            created_at=investment.created_at,
            updated_at=investment.updated_at,
            held_to_maturity=investment.held_to_maturity,
            face_value=(
                investment.face_value.amount
                if investment.face_value is not None
                else None
            ),
            face_value_currency=(
                investment.face_value.currency
                if investment.face_value is not None
                else "USD"
            ),
            name=investment.name,
        )
