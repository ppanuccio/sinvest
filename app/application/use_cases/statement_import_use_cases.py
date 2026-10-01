"""Statement import use cases - bulk-create investments and transactions."""

import re
from typing import Dict, List, Optional

from app.application.dto.import_dto import (
    ImportResultDTO,
    ImportedTransactionDTO,
    InvalidIdentifierDTO,
)
from app.application.dto.investment_dto import CreateInvestmentDTO
from app.application.dto.transaction_dto import CreateTransactionDTO
from app.application.identifier_validation import (
    IdentifierValidator,
    ValidationResult,
)
from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.transaction_use_cases import TransactionUseCases
from app.domain.exceptions import (
    EntityNotFoundException,
    InvalidIdentifierException,
    UnauthorizedException,
)
from app.domain.repositories.investment_repository import InvestmentRepository
from app.domain.repositories.portfolio_repository import PortfolioRepository
from app.domain.repositories.transaction_repository import TransactionRepository


class StatementImportUseCases:
    """Import parsed statement rows into a user's portfolio.

    Reuses the single-item use cases so validation, value objects and
    persistence behave exactly like a manually entered row. Rows referring
    to an identifier that has no investment yet get one created on the fly
    (asset class from the external validator when available, else guessed
    from the security name); rows that exactly match an existing transaction
    (same investment, date, kind, amount and quantity) are skipped, so
    importing the same file twice is harmless.

    New identifiers are validated in one batched pass before the row loop
    (external reference data via the optional IdentifierValidator). Rows
    whose identifier fails validation are skipped and reported in the
    result instead of aborting the import.
    """

    # Security-name fragments that identify fund/ETF products in bank
    # statement exports (e.g. "ISHS CR WD USD-AC", "XTR2 EUR OR SW 1CC").
    _ETF_NAME_FRAGMENTS = (
        "ISHS",
        "ISHARES",
        "XTR",
        "XTRACKERS",
        "LYXOR",
        "LYX",
        "VANGUARD",
        "VANG",
        "AMUNDI",
        "AMUN",
        "UBS ETF",
    )
    # An explicit coupon in the name ("IBRD-17NV28 3%") marks a bond.
    _COUPON_PATTERN = re.compile(r"\d[,.]?\d*\s*%")

    def __init__(
        self,
        investment_use_cases: InvestmentUseCases,
        transaction_use_cases: TransactionUseCases,
        portfolio_repository: PortfolioRepository,
        investment_repository: InvestmentRepository,
        transaction_repository: TransactionRepository,
        identifier_validator: Optional[IdentifierValidator] = None,
    ):
        self.investment_use_cases = investment_use_cases
        self.transaction_use_cases = transaction_use_cases
        self.portfolio_repository = portfolio_repository
        self.investment_repository = investment_repository
        self.transaction_repository = transaction_repository
        self.identifier_validator = identifier_validator

    def import_transactions(
        self,
        user_id: str,
        portfolio_id: str,
        rows: List[ImportedTransactionDTO],
        broker: str,
    ) -> ImportResultDTO:
        """Create missing investments and all transactions for the rows."""
        portfolio = self.portfolio_repository.get_by_id(portfolio_id)
        if not portfolio:
            raise EntityNotFoundException("Portfolio", portfolio_id)
        if portfolio.user_id != user_id:
            raise UnauthorizedException(f"User {user_id} does not own portfolio {portfolio_id}")

        result = ImportResultDTO()

        # Map identifier -> investment id so several rows of the same security
        # only create (and look up) one investment. Keys are uppercased to
        # match what the domain stores.
        investment_ids = {
            inv.identifier.value: inv.id
            for inv in self.investment_repository.list_by_portfolio(portfolio_id)
        }

        # Group rows by normalized identifier; validate the distinct new ones
        # in a single batched pass before touching the repositories.
        rows_by_key: Dict[str, List[ImportedTransactionDTO]] = {}
        for row in rows:
            key = row.identifier.strip().upper()
            rows_by_key.setdefault(key, []).append(row)

        pending = [k for k in rows_by_key if k not in investment_ids]
        validation: Dict[str, ValidationResult] = {}
        if self.identifier_validator is not None and pending:
            validation = self.identifier_validator.validate_many(pending, "ISIN")

        for row in rows:
            key = row.identifier.strip().upper()
            outcome = validation.get(key)

            if outcome is not None and not outcome.is_valid:
                result.invalid_identifiers.append(
                    InvalidIdentifierDTO(
                        identifier=key,
                        title=row.title,
                        reason=outcome.message or "Invalid ISIN",
                    )
                )
                continue

            investment_id = investment_ids.get(key)
            if investment_id is None:
                try:
                    investment = self.investment_use_cases.create_investment(
                        user_id,
                        CreateInvestmentDTO(
                            portfolio_id=portfolio_id,
                            identifier=key,
                            identifier_type="ISIN",
                            type=self._resolve_type(row.title, outcome),
                            name=self._resolve_name(row, outcome),
                        ),
                    )
                except InvalidIdentifierException as exc:
                    # The domain rejected the identifier (e.g. bad check digit
                    # with no external validator wired) — skip and report.
                    result.invalid_identifiers.append(
                        InvalidIdentifierDTO(
                            identifier=key,
                            title=row.title,
                            reason=str(exc),
                        )
                    )
                    continue
                result.created_investments.append(investment)
                investment_ids[key] = investment.id
                investment_id = investment.id

            if self._transaction_exists(investment_id, row):
                result.skipped_transactions += 1
                continue

            self.transaction_use_cases.create_transaction(
                user_id,
                CreateTransactionDTO(
                    investment_id=investment_id,
                    amount=row.amount,
                    quantity=row.quantity,
                    broker=broker,
                    date=row.date,
                    currency=row.currency,
                    kind=row.kind,
                ),
            )
            result.created_transactions += 1

        return result

    def _guess_investment_type(self, title: str) -> str:
        """Guess the asset class from the security name in the statement."""
        name = title.upper()
        if any(fragment in name for fragment in self._ETF_NAME_FRAGMENTS):
            return "etf"
        if self._COUPON_PATTERN.search(name):
            return "bond"
        return "other"

    def _resolve_type(
        self, title: str, outcome: Optional[ValidationResult]
    ) -> str:
        """Prefer the validator's normalized type; fall back to the title guess."""
        if outcome is not None and outcome.security_type:
            return outcome.security_type
        return self._guess_investment_type(title)

    @staticmethod
    def _resolve_name(
        row: ImportedTransactionDTO, outcome: Optional[ValidationResult]
    ) -> Optional[str]:
        """Keep the broker title unless it just repeats the ISIN; then the
        validator's name, then whatever title remains."""
        title = (row.title or "").strip()
        if title and title.upper() != row.identifier.strip().upper():
            return title
        if outcome is not None and outcome.name:
            return outcome.name
        return title or None

    def _transaction_exists(self, investment_id: str, row: ImportedTransactionDTO) -> bool:
        """Detect a row already imported earlier (same date/kind/amount/qty)."""
        existing = self.transaction_repository.list_by_investment(investment_id)
        for tx in existing:
            if (
                tx.date == row.date
                and getattr(tx, "kind", "buy") == row.kind
                and tx.amount.amount == row.amount
                and tx.amount.currency == row.currency
                and tx.quantity.value == row.quantity
            ):
                return True
        return False
