"""Transaction use cases - orchestrates transaction operations."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List

from app.domain.entities.transaction import Transaction
from app.domain.repositories.transaction_repository import TransactionRepository
from app.domain.repositories.investment_repository import InvestmentRepository
from app.domain.repositories.portfolio_repository import PortfolioRepository
from app.domain.value_objects import Money, Quantity
from app.domain.services.validation_service import ValidationService
from app.domain.exceptions import (
    EntityNotFoundException,
    UnauthorizedException,
)
from app.application.dto.transaction_dto import (
    CreateTransactionDTO,
    UpdateTransactionDTO,
    TransactionResponseDTO,
)


class TransactionUseCases:
    """Orchestrates all transaction-related operations."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        investment_repository: InvestmentRepository,
        portfolio_repository: PortfolioRepository,
    ):
        self.transaction_repository = transaction_repository
        self.investment_repository = investment_repository
        self.portfolio_repository = portfolio_repository
        self.validation_service = ValidationService()

    def create_transaction(
        self, user_id: str, dto: CreateTransactionDTO
    ) -> TransactionResponseDTO:
        """Create a new transaction for an investment."""
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

        # Validate transaction data
        self.validation_service.validate_transaction_amount(dto.amount)
        self.validation_service.validate_transaction_quantity(dto.quantity)
        self.validation_service.validate_transaction_broker(dto.broker)
        self.validation_service.validate_transaction_date(dto.date)

        # Create value objects
        money = Money(dto.amount, dto.currency)
        quantity = Quantity(dto.quantity)

        # Create transaction entity
        transaction = Transaction(
            id=str(uuid.uuid4()),
            investment_id=dto.investment_id,
            amount=money,
            quantity=quantity,
            broker=dto.broker,
            date=dto.date,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Save and return
        saved = self.transaction_repository.save(transaction)
        return self._to_response_dto(saved)

    def get_transaction(
        self, transaction_id: str, user_id: str
    ) -> TransactionResponseDTO:
        """Get a transaction by ID with authorization check."""
        transaction = self.transaction_repository.get_by_id(transaction_id)
        if not transaction:
            raise EntityNotFoundException("Transaction", transaction_id)

        # Verify user owns the investment
        investment = self.investment_repository.get_by_id(
            transaction.investment_id
        )
        if not investment:
            raise EntityNotFoundException("Investment", transaction.investment_id)

        portfolio = self.portfolio_repository.get_by_id(
            investment.portfolio_id
        )
        if not portfolio or portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own transaction {transaction_id}"
            )

        return self._to_response_dto(transaction)

    def list_transactions(
        self, investment_id: str, user_id: str
    ) -> List[TransactionResponseDTO]:
        """List all transactions for an investment."""
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

        transactions = self.transaction_repository.list_by_investment(
            investment_id
        )
        return [self._to_response_dto(t) for t in transactions]

    def update_transaction(
        self, transaction_id: str, user_id: str, dto: UpdateTransactionDTO
    ) -> TransactionResponseDTO:
        """Update a transaction."""
        # Get and verify ownership
        transaction = self.transaction_repository.get_by_id(transaction_id)
        if not transaction:
            raise EntityNotFoundException("Transaction", transaction_id)

        investment = self.investment_repository.get_by_id(
            transaction.investment_id
        )
        if not investment:
            raise EntityNotFoundException("Investment", transaction.investment_id)

        portfolio = self.portfolio_repository.get_by_id(
            investment.portfolio_id
        )
        if not portfolio or portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own transaction {transaction_id}"
            )

        # Validate and update fields
        updated_amount = None
        updated_quantity = None
        updated_broker = dto.broker
        updated_date = dto.date

        if dto.amount is not None:
            self.validation_service.validate_transaction_amount(dto.amount)
            currency = dto.currency or transaction.amount.currency
            updated_amount = Money(dto.amount, currency)

        if dto.quantity is not None:
            self.validation_service.validate_transaction_quantity(
                dto.quantity
            )
            updated_quantity = Quantity(dto.quantity)

        if updated_broker:
            self.validation_service.validate_transaction_broker(updated_broker)

        if updated_date:
            self.validation_service.validate_transaction_date(updated_date)

        # Update entity
        transaction.update_details(
            amount=updated_amount,
            quantity=updated_quantity,
            broker=updated_broker,
            date=updated_date,
            updated_at=datetime.utcnow(),
        )

        updated = self.transaction_repository.update(transaction)
        return self._to_response_dto(updated)

    def delete_transaction(self, transaction_id: str, user_id: str) -> None:
        """Delete a transaction."""
        # Get and verify ownership
        transaction = self.transaction_repository.get_by_id(transaction_id)
        if not transaction:
            raise EntityNotFoundException("Transaction", transaction_id)

        investment = self.investment_repository.get_by_id(
            transaction.investment_id
        )
        if not investment:
            raise EntityNotFoundException("Investment", transaction.investment_id)

        portfolio = self.portfolio_repository.get_by_id(
            investment.portfolio_id
        )
        if not portfolio or portfolio.user_id != user_id:
            raise UnauthorizedException(
                f"User {user_id} does not own transaction {transaction_id}"
            )

        # Delete
        self.transaction_repository.delete(transaction_id)

    def _to_response_dto(self, transaction: Transaction) -> TransactionResponseDTO:
        """Convert transaction entity to response DTO."""
        return TransactionResponseDTO(
            id=transaction.id,
            investment_id=transaction.investment_id,
            amount=transaction.amount.amount,
            quantity=transaction.quantity.value,
            broker=transaction.broker,
            date=transaction.date,
            created_at=transaction.created_at,
            updated_at=transaction.updated_at,
            currency=transaction.amount.currency,
        )
