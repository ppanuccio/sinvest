"""CLI entrypoint for the investment portfolio application."""

import argparse
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

# Ensure package imports work when executing this file directly.
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.infrastructure.in_memory_repositories import (
    InMemoryInvestmentRepository,
    InMemoryPortfolioRepository,
    InMemoryPriceHistoryRepository,
    InMemoryTransactionRepository,
    InMemoryUserRepository,
)
from app.infrastructure.file_based_repositories import (
    FileBasedInvestmentRepository,
    FileBasedPortfolioRepository,
    FileBasedPriceHistoryRepository,
    FileBasedTransactionRepository,
    FileBasedUserRepository,
)
from app.application.use_cases.user_use_cases import UserUseCases
from app.application.use_cases.portfolio_use_cases import PortfolioUseCases
from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.transaction_use_cases import TransactionUseCases
from app.application.dto.user_dto import CreateUserDTO
from app.application.dto.portfolio_dto import CreatePortfolioDTO
from app.application.dto.investment_dto import CreateInvestmentDTO
from app.application.dto.transaction_dto import CreateTransactionDTO



class CLI:
    def __init__(self, use_file_persistence: bool = False):
        if use_file_persistence:
            self.user_repo = FileBasedUserRepository()
            self.portfolio_repo = FileBasedPortfolioRepository()
            self.investment_repo = FileBasedInvestmentRepository()
            self.transaction_repo = FileBasedTransactionRepository()
            self.price_history_repo = FileBasedPriceHistoryRepository()
        else:
            self.user_repo = InMemoryUserRepository()
            self.portfolio_repo = InMemoryPortfolioRepository()
            self.investment_repo = InMemoryInvestmentRepository()
            self.transaction_repo = InMemoryTransactionRepository()
            self.price_history_repo = InMemoryPriceHistoryRepository()

        self.user_use_cases = UserUseCases(self.user_repo)
        self.portfolio_use_cases = PortfolioUseCases(self.portfolio_repo)
        self.investment_use_cases = InvestmentUseCases(
            self.investment_repo, self.portfolio_repo
        )
        self.transaction_use_cases = TransactionUseCases(
            self.transaction_repo,
            self.investment_repo,
            self.portfolio_repo,
        )

    def run(self, args: Any) -> None:
        # First, parse global flags
        global_parser = argparse.ArgumentParser(add_help=False)
        global_parser.add_argument(
            "--persist",
            action="store_true",
            help="Use file-based persistence",
        )
        global_args, remaining = global_parser.parse_known_args(args)
        
        # Reinitialize repos if persistence is requested
        if global_args.persist:
            self.user_repo = FileBasedUserRepository()
            self.portfolio_repo = FileBasedPortfolioRepository()
            self.investment_repo = FileBasedInvestmentRepository()
            self.transaction_repo = FileBasedTransactionRepository()
            self.price_history_repo = FileBasedPriceHistoryRepository()
            
            self.user_use_cases = UserUseCases(self.user_repo)
            self.portfolio_use_cases = PortfolioUseCases(self.portfolio_repo)
            self.investment_use_cases = InvestmentUseCases(
                self.investment_repo, self.portfolio_repo
            )
            self.transaction_use_cases = TransactionUseCases(
                self.transaction_repo,
                self.investment_repo,
                self.portfolio_repo,
            )
        
        # Now parse the subcommand
        parser = argparse.ArgumentParser(
            description="Investment portfolio CLI"
        )
        parser.add_argument(
            "--persist",
            action="store_true",
            help="Use file-based persistence (data stored in data/ directory)",
        )
        subparsers = parser.add_subparsers(dest="command", required=True)

        self._add_create_user(subparsers)
        self._add_create_portfolio(subparsers)
        self._add_create_investment(subparsers)
        self._add_create_transaction(subparsers)
        self._add_list_portfolios(subparsers)
        self._add_show_portfolio(subparsers)
        self._add_list_investments(subparsers)
        self._add_list_transactions(subparsers)

        parsed = parser.parse_args(args)
        try:
            command = parsed.command
            if command == "create-user":
                self._handle_create_user(parsed)
            elif command == "create-portfolio":
                self._handle_create_portfolio(parsed)
            elif command == "create-investment":
                self._handle_create_investment(parsed)
            elif command == "create-transaction":
                self._handle_create_transaction(parsed)
            elif command == "list-portfolios":
                self._handle_list_portfolios(parsed)
            elif command == "show-portfolio":
                self._handle_show_portfolio(parsed)
            elif command == "list-investments":
                self._handle_list_investments(parsed)
            elif command == "list-transactions":
                self._handle_list_transactions(parsed)
            else:
                parser.print_help()
        except Exception as exc:
            print(f"ERROR: {exc}")

    def _add_create_user(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("create-user", help="Create a new user")
        parser.add_argument("username", type=str, help="Username")
        parser.add_argument("email", type=str, help="Email address")
        parser.add_argument("password", type=str, help="Password")

    def _add_create_portfolio(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "create-portfolio", help="Create a new portfolio"
        )
        parser.add_argument("user_id", type=str, help="User ID")
        parser.add_argument("name", type=str, help="Portfolio name")
        parser.add_argument(
            "--description", type=str, default=None, help="Portfolio description"
        )

    def _add_create_investment(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "create-investment", help="Create a new investment"
        )
        parser.add_argument("user_id", type=str, help="User ID")
        parser.add_argument("portfolio_id", type=str, help="Portfolio ID")
        parser.add_argument("identifier", type=str, help="ISIN or ticker")
        parser.add_argument(
            "identifier_type",
            type=str,
            choices=["ISIN", "TICKER"],
            help="Identifier type",
        )
        parser.add_argument(
            "type",
            type=str,
            choices=["stock", "bond", "etf", "crypto", "mutual_fund", "commodity", "other"],
            help="Investment type",
        )

    def _add_create_transaction(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "create-transaction", help="Create a new transaction"
        )
        parser.add_argument("user_id", type=str, help="User ID")
        parser.add_argument("investment_id", type=str, help="Investment ID")
        parser.add_argument("amount", type=Decimal, help="Transaction amount")
        parser.add_argument("quantity", type=Decimal, help="Transaction quantity")
        parser.add_argument("broker", type=str, help="Broker name")
        parser.add_argument(
            "date",
            type=str,
            help="Transaction date in ISO format, e.g. 2026-05-23T15:30:00",
        )

    def _add_list_portfolios(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "list-portfolios",
            help="List all portfolios for a user",
        )
        parser.add_argument("user_id", type=str, help="User ID")

    def _add_show_portfolio(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "show-portfolio",
            help="Show a portfolio and its investments",
        )
        parser.add_argument("user_id", type=str, help="User ID")
        parser.add_argument("portfolio_id", type=str, help="Portfolio ID")

    def _add_list_investments(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "list-investments",
            help="List investments in a portfolio",
        )
        parser.add_argument("user_id", type=str, help="User ID")
        parser.add_argument("portfolio_id", type=str, help="Portfolio ID")

    def _add_list_transactions(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "list-transactions",
            help="List transactions for an investment",
        )
        parser.add_argument("user_id", type=str, help="User ID")
        parser.add_argument("investment_id", type=str, help="Investment ID")

    def _handle_create_user(self, parsed: Any) -> None:
        dto = CreateUserDTO(
            username=parsed.username,
            email=parsed.email,
            password=parsed.password,
        )
        user = self.user_use_cases.create_user(dto)
        self._print_user(user)

    def _handle_create_portfolio(self, parsed: Any) -> None:
        dto = CreatePortfolioDTO(
            user_id=parsed.user_id,
            name=parsed.name,
            description=parsed.description,
        )
        portfolio = self.portfolio_use_cases.create_portfolio(
            parsed.user_id, dto
        )
        self._print_portfolio(portfolio)

    def _handle_create_investment(self, parsed: Any) -> None:
        dto = CreateInvestmentDTO(
            portfolio_id=parsed.portfolio_id,
            identifier=parsed.identifier,
            identifier_type=parsed.identifier_type,
            type=parsed.type,
        )
        investment = self.investment_use_cases.create_investment(
            parsed.user_id, dto
        )
        self._print_investment(investment)

    def _handle_create_transaction(self, parsed: Any) -> None:
        transaction_date = self._parse_date(parsed.date)
        dto = CreateTransactionDTO(
            investment_id=parsed.investment_id,
            amount=parsed.amount,
            quantity=parsed.quantity,
            broker=parsed.broker,
            date=transaction_date,
        )
        transaction = self.transaction_use_cases.create_transaction(
            parsed.user_id, dto
        )
        self._print_transaction(transaction)

    def _handle_list_portfolios(self, parsed: Any) -> None:
        portfolios = self.portfolio_use_cases.list_portfolios(
            parsed.user_id
        )
        if not portfolios:
            print("No portfolios found.")
            return
        for portfolio in portfolios:
            self._print_portfolio(portfolio)
            print("-")

    def _handle_show_portfolio(self, parsed: Any) -> None:
        portfolio = self.portfolio_use_cases.get_portfolio(
            parsed.portfolio_id, parsed.user_id
        )
        self._print_portfolio(portfolio)
        investments = self.investment_use_cases.list_investments(
            parsed.portfolio_id, parsed.user_id
        )
        print("Investments:")
        if not investments:
            print("  No investments found.")
            return
        for investment in investments:
            print(f"  - {investment.id}: {investment.identifier} ({investment.type})")
            transactions = self.transaction_use_cases.list_transactions(
                investment.id, parsed.user_id
            )
            print(f"      Transactions: {len(transactions)}")

    def _handle_list_investments(self, parsed: Any) -> None:
        investments = self.investment_use_cases.list_investments(
            parsed.portfolio_id, parsed.user_id
        )
        if not investments:
            print("No investments found.")
            return
        for investment in investments:
            self._print_investment(investment)
            print("-")

    def _handle_list_transactions(self, parsed: Any) -> None:
        transactions = self.transaction_use_cases.list_transactions(
            parsed.investment_id, parsed.user_id
        )
        if not transactions:
            print("No transactions found.")
            return
        for transaction in transactions:
            self._print_transaction(transaction)
            print("-")

    def _parse_date(self, date_text: str) -> datetime:
        try:
            return datetime.fromisoformat(date_text)
        except ValueError as exc:
            raise ValueError(
                "Date must be in ISO format like 2026-05-23T15:30:00"
            ) from exc

    def _print_user(self, user: Any) -> None:
        print("User created:")
        print(f"  id: {user.id}")
        print(f"  username: {user.username}")
        print(f"  email: {user.email}")
        print(f"  created_at: {user.created_at}")

    def _print_portfolio(self, portfolio: Any) -> None:
        print("Portfolio:")
        print(f"  id: {portfolio.id}")
        print(f"  user_id: {portfolio.user_id}")
        print(f"  name: {portfolio.name}")
        print(f"  description: {portfolio.description}")
        print(f"  created_at: {portfolio.created_at}")
        print(f"  updated_at: {portfolio.updated_at}")

    def _print_investment(self, investment: Any) -> None:
        print("Investment:")
        print(f"  id: {investment.id}")
        print(f"  portfolio_id: {investment.portfolio_id}")
        print(f"  identifier: {investment.identifier}")
        print(f"  identifier_type: {investment.identifier_type}")
        print(f"  type: {investment.type}")
        print(f"  created_at: {investment.created_at}")
        print(f"  updated_at: {investment.updated_at}")

    def _print_transaction(self, transaction: Any) -> None:
        print("Transaction:")
        print(f"  id: {transaction.id}")
        print(f"  investment_id: {transaction.investment_id}")
        print(f"  amount: {transaction.amount}")
        print(f"  quantity: {transaction.quantity}")
        print(f"  broker: {transaction.broker}")
        print(f"  date: {transaction.date}")
        print(f"  created_at: {transaction.created_at}")
        print(f"  updated_at: {transaction.updated_at}")


def main() -> None:
    import sys

    # Check for --persist flag
    use_persist = "--persist" in sys.argv
    
    cli = CLI(use_file_persistence=use_persist)
    cli.run(sys.argv[1:])


if __name__ == "__main__":
    main()
