"""
Domain exceptions - all exceptions that can be raised by domain logic.
These are framework-agnostic and represent business rule violations.
"""


class DomainException(Exception):
    """Base exception for all domain-level errors."""

    pass


class EntityNotFoundException(DomainException):
    """Raised when an entity cannot be found."""

    def __init__(self, entity_type: str, entity_id: str | int):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            f"{entity_type} with id '{entity_id}' not found"
        )


class UnauthorizedException(DomainException):
    """Raised when a user tries to access a resource they don't own."""

    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(message)


class InvalidIdentifierException(DomainException):
    """Raised when an investment identifier (ISIN or ticker) is invalid."""

    def __init__(self, identifier: str, message: str = ""):
        self.identifier = identifier
        msg = f"Invalid identifier '{identifier}'"
        if message:
            msg += f": {message}"
        super().__init__(msg)


class InvalidTransactionException(DomainException):
    """Raised when transaction data is invalid."""

    def __init__(self, message: str):
        super().__init__(f"Invalid transaction: {message}")


class InvalidPortfolioException(DomainException):
    """Raised when portfolio data is invalid."""

    def __init__(self, message: str):
        super().__init__(f"Invalid portfolio: {message}")


class InvalidInvestmentException(DomainException):
    """Raised when investment data is invalid."""

    def __init__(self, message: str):
        super().__init__(f"Invalid investment: {message}")


class DuplicateUserException(DomainException):
    """Raised when attempting to create a user that already exists."""

    def __init__(self, username: str):
        self.username = username
        super().__init__(f"User with username '{username}' already exists")
