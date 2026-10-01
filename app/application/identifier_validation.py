"""Identifier-enrichment port: external reference-data validation for identifiers.

The application defines the contract; infrastructure provides the adapter
(e.g. OpenFIGI). The contract is deliberately failure-tolerant: validation is
an enrichment step for imports, never a hard dependency.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Sequence


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating one identifier against external reference data.

    is_valid=True means "import may proceed": either the security was verified
    against the reference database, or the identifier is well-formed but not
    listed there, or the service was unreachable (soft-pass). Only
    is_valid=False — a provider-reported invalid identifier — blocks a row.
    """

    is_valid: bool
    name: Optional[str] = None  # Security name when known
    security_type: Optional[str] = None  # Normalized: "stock" | "bond" | "etf"
    message: Optional[str] = None  # Error/warning/unavailability detail


class IdentifierValidator(ABC):
    """Validate identifiers against external reference data and enrich results."""

    @abstractmethod
    def validate(self, identifier: str, identifier_type: str = "ISIN") -> ValidationResult:
        """Validate a single identifier."""
        pass

    @abstractmethod
    def validate_many(
        self, identifiers: Sequence[str], identifier_type: str = "ISIN"
    ) -> Dict[str, ValidationResult]:
        """Validate a batch; results keyed by the uppercased identifier."""
        pass
