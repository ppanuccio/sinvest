"""Portfolio use cases - orchestrates portfolio operations."""

import uuid
from datetime import datetime
from typing import List

from app.domain.entities.portfolio import Portfolio
from app.domain.repositories.portfolio_repository import PortfolioRepository
from app.domain.services.validation_service import ValidationService
from app.domain.exceptions import EntityNotFoundException, UnauthorizedException
from app.application.dto.portfolio_dto import (
    CreatePortfolioDTO,
    UpdatePortfolioDTO,
    PortfolioResponseDTO,
    PortfolioDetailResponseDTO,
)


class PortfolioUseCases:
    """Orchestrates all portfolio-related operations."""

    def __init__(self, portfolio_repository: PortfolioRepository):
        self.portfolio_repository = portfolio_repository
        self.validation_service = ValidationService()

    def create_portfolio(
        self, user_id: str, dto: CreatePortfolioDTO
    ) -> PortfolioResponseDTO:
        """Create a new portfolio for a user."""
        # Validate input
        self.validation_service.validate_portfolio_name(dto.name)

        # Ensure user_id matches (security check)
        if dto.user_id != user_id:
            raise UnauthorizedException(
                "Cannot create portfolio for another user"
            )

        # Create portfolio entity
        portfolio = Portfolio(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=dto.name,
            description=dto.description,
            created_at=datetime.utcnow(),
        )

        # Save and return
        saved = self.portfolio_repository.save(portfolio)
        return self._to_response_dto(saved)

    def get_portfolio(
        self, portfolio_id: str, user_id: str
    ) -> PortfolioResponseDTO:
        """Get a portfolio by ID with authorization check."""
        portfolio = self.portfolio_repository.get_by_id(portfolio_id)
        if not portfolio:
            raise EntityNotFoundException("Portfolio", portfolio_id)

        # Verify user owns this portfolio
        if portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own portfolio {portfolio_id}"
            )

        return self._to_response_dto(portfolio)

    def list_portfolios(self, user_id: str) -> List[PortfolioResponseDTO]:
        """List all portfolios for a user."""
        portfolios = self.portfolio_repository.list_by_user(user_id)
        return [self._to_response_dto(p) for p in portfolios]

    def update_portfolio(
        self, portfolio_id: str, user_id: str, dto: UpdatePortfolioDTO
    ) -> PortfolioResponseDTO:
        """Update a portfolio."""
        # Get and verify ownership
        portfolio = self.portfolio_repository.get_by_id(portfolio_id)
        if not portfolio:
            raise EntityNotFoundException("Portfolio", portfolio_id)

        if portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own portfolio {portfolio_id}"
            )

        # Validate input if provided
        if dto.name:
            self.validation_service.validate_portfolio_name(dto.name)

        # Update and save
        portfolio.update_details(
            name=dto.name,
            description=dto.description,
            updated_at=datetime.utcnow(),
        )
        updated = self.portfolio_repository.update(portfolio)

        return self._to_response_dto(updated)

    def delete_portfolio(self, portfolio_id: str, user_id: str) -> None:
        """Delete a portfolio."""
        # Get and verify ownership
        portfolio = self.portfolio_repository.get_by_id(portfolio_id)
        if not portfolio:
            raise EntityNotFoundException("Portfolio", portfolio_id)

        if portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own portfolio {portfolio_id}"
            )

        # Delete
        self.portfolio_repository.delete(portfolio_id)

    def _to_response_dto(self, portfolio: Portfolio) -> PortfolioResponseDTO:
        """Convert portfolio entity to response DTO."""
        return PortfolioResponseDTO(
            id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            description=portfolio.description,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
        )
