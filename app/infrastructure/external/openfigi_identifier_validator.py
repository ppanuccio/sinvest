"""OpenFIGI-backed identifier validator.

Validates ISINs against the OpenFIGI mapping API (free, no API key needed;
25 requests/minute unauthenticated, max 10 jobs per request — both verified
against the live service). Enriches results with the security name and a
normalized security type.
"""

import time
from typing import Dict, Optional, Sequence

import httpx

from app.application.identifier_validation import (
    IdentifierValidator,
    ValidationResult,
)


class OpenFigiIdentifierValidator(IdentifierValidator):
    """Validate identifiers against OpenFIGI reference data.

    Failure semantics (mirroring the port contract): only an
    ``{"error": ...}`` mapping entry marks an identifier invalid. An
    unlisted-but-well-formed identifier (``{"warning": ...}``), a network
    error, a rate limit, or an unexpected response all soft-pass as valid
    so a validation outage never blocks an import. Only definitive
    outcomes are cached.
    """

    _BATCH_SIZE = 10  # Unauthenticated mapping requests cap at 10 jobs.
    _MIN_REQUEST_INTERVAL = 2.5  # Unauthenticated limit: 25 requests/minute.
    _SECURITY_TYPE_MAP = {
        "govt": "bond",
        "corp": "bond",
        "sovrgn": "bond",
        "muni": "bond",
        "etf": "etf",
        "common stock": "stock",
    }

    def __init__(
        self,
        base_url: str = "https://api.openfigi.com/v3",
        timeout: float = 5.0,
        api_key: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-OPENFIGI-API-KEY"] = api_key
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers=headers,
            transport=transport,
        )
        self._cache: Dict[str, ValidationResult] = {}
        self._last_request_at: Optional[float] = None

    def validate(self, identifier: str, identifier_type: str = "ISIN") -> ValidationResult:
        return self.validate_many([identifier], identifier_type)[identifier.strip().upper()]

    def validate_many(
        self, identifiers: Sequence[str], identifier_type: str = "ISIN"
    ) -> Dict[str, ValidationResult]:
        keys = [i.strip().upper() for i in identifiers]
        results: Dict[str, ValidationResult] = {}

        if identifier_type.upper() != "ISIN":
            # OpenFIGI mapping needs exchange codes for tickers — unreliable,
            # so external validation is ISIN-only.
            soft = ValidationResult(
                is_valid=True,
                message="External validation supports ISINs only",
            )
            return {key: soft for key in keys}

        missing = []
        for key in keys:
            cached = self._cache.get(key)
            if cached is not None:
                results[key] = cached
            elif key not in missing:
                missing.append(key)

        for chunk_start in range(0, len(missing), self._BATCH_SIZE):
            chunk = missing[chunk_start : chunk_start + self._BATCH_SIZE]
            self._pace_requests()
            chunk_results = self._request_chunk(chunk)
            for key, (outcome, definitive) in chunk_results.items():
                results[key] = outcome
                if definitive:
                    self._cache[key] = outcome

        return results

    def _pace_requests(self) -> None:
        """Sleep just long enough to respect the per-minute request limit."""
        if self._last_request_at is None:
            self._last_request_at = time.monotonic()
            return
        elapsed = time.monotonic() - self._last_request_at
        wait = self._MIN_REQUEST_INTERVAL - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def _request_chunk(self, chunk: Sequence[str]) -> Dict[str, "tuple[ValidationResult, bool]"]:
        """Map one batch of ISINs; the bool marks definitive outcomes (cacheable)."""
        jobs = [{"idType": "ID_ISIN", "idValue": isin} for isin in chunk]
        try:
            response = self._client.post("/mapping", json=jobs)
        except httpx.HTTPError as exc:
            return self._soft_pass_chunk(chunk, f"External ISIN validation unavailable: {exc}")

        if response.status_code == 429:
            return self._soft_pass_chunk(chunk, "External ISIN validation rate limited")
        if response.status_code != 200:
            return self._soft_pass_chunk(
                chunk,
                f"External ISIN validation unavailable (HTTP {response.status_code})",
            )

        try:
            entries = response.json()
        except ValueError:
            return self._soft_pass_chunk(chunk, "Unexpected OpenFIGI response")

        outcomes: Dict[str, "tuple[ValidationResult, bool]"] = {}
        for isin, entry in zip(chunk, entries):
            outcomes[isin] = self._interpret_entry(entry)
        return outcomes

    @staticmethod
    def _soft_pass_chunk(
        chunk: Sequence[str], message: str
    ) -> Dict[str, "tuple[ValidationResult, bool]"]:
        # Non-definitive: the service said nothing usable, so never cache —
        # a later import should retry.
        return {isin: (ValidationResult(is_valid=True, message=message), False) for isin in chunk}

    def _interpret_entry(self, entry: dict) -> "tuple[ValidationResult, bool]":
        """Translate one mapping entry into (outcome, definitive)."""
        if not isinstance(entry, dict):
            return (
                ValidationResult(is_valid=True, message="Unexpected OpenFIGI response"),
                False,
            )
        if "error" in entry:
            return ValidationResult(is_valid=False, message=entry["error"]), True
        if "warning" in entry:
            # Well-formed identifier that FIGI does not list — still import.
            return ValidationResult(is_valid=True, message=entry["warning"]), True
        data = entry.get("data")
        if not data or not isinstance(data, list):
            return (
                ValidationResult(is_valid=True, message="Unexpected OpenFIGI response"),
                False,
            )
        record = data[0] if isinstance(data[0], dict) else {}
        return (
            ValidationResult(
                is_valid=True,
                name=record.get("name"),
                security_type=self._normalize_type(record.get("securityType2")),
            ),
            True,
        )

    def _normalize_type(self, security_type2: Optional[str]) -> Optional[str]:
        if not security_type2:
            return None
        return self._SECURITY_TYPE_MAP.get(security_type2.strip().lower())
