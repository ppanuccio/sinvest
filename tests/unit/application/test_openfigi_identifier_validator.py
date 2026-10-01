"""Tests for the OpenFIGI identifier validator adapter."""

import httpx
import pytest

from app.application.identifier_validation import ValidationResult
from app.infrastructure.external.openfigi_identifier_validator import (
    OpenFigiIdentifierValidator,
)


def make_validator(payload=None, exc=None, status_code=200):
    """Build a validator backed by a MockTransport; call count is tracked."""
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if exc is not None:
            raise exc
        return httpx.Response(status_code, json=payload or [])

    validator = OpenFigiIdentifierValidator(transport=httpx.MockTransport(handler))
    validator._MIN_REQUEST_INTERVAL = 0  # keep tests fast
    return validator, calls


def mapping_entry(name="BUONI POLIENNALI DEL TES", security_type2="Govt"):
    return {
        "data": [
            {
                "figi": "BBG01B6TQMG0",
                "name": name,
                "ticker": "BTPS 4.4 05/01/33 10Y",
                "exchCode": "MOT",
                "securityType2": security_type2,
            }
        ]
    }


class TestOpenFigiIdentifierValidator:
    def test_success_batch_returns_names_and_types(self):
        payload = [
            mapping_entry("APPLE INC", "Common Stock"),
            mapping_entry("BUONI POLIENNALI DEL TES", "Govt"),
        ]
        validator, calls = make_validator(payload=payload)

        results = validator.validate_many(["US0378331005", "IT0005518128"])

        assert calls["count"] == 1
        assert results["US0378331005"].is_valid
        assert results["US0378331005"].name == "APPLE INC"
        assert results["US0378331005"].security_type == "stock"
        assert results["IT0005518128"].name == "BUONI POLIENNALI DEL TES"
        assert results["IT0005518128"].security_type == "bond"

    def test_mixed_batch_maps_entries_by_index(self):
        payload = [
            mapping_entry(),
            {"error": "Invalid idValue format."},
            {"warning": "No identifier found."},
        ]
        validator, calls = make_validator(payload=payload)

        results = validator.validate_many(["IT0005518128", "IT0005322855", "IT0005532715"])

        assert calls["count"] == 1
        assert results["IT0005518128"].is_valid
        assert results["IT0005518128"].name == "BUONI POLIENNALI DEL TES"
        assert results["IT0005322855"].is_valid is False
        assert "Invalid idValue format." in results["IT0005322855"].message
        assert results["IT0005532715"].is_valid is True
        assert results["IT0005532715"].name is None

    def test_chunking_over_batch_size(self):
        # 35 ISINs -> 4 calls (10+10+10+5).
        payload = [mapping_entry() for _ in range(10)]
        validator, calls = make_validator(payload=payload)

        isins = [f"IT000{i:09d}" for i in range(35)]
        results = validator.validate_many(isins)

        assert calls["count"] == 4
        assert len(results) == 35
        assert all(outcome.is_valid for outcome in results.values())

    def test_cache_prevents_repeat_requests(self):
        validator, calls = make_validator(payload=[mapping_entry()])

        first = validator.validate("IT0005518128")
        second = validator.validate("IT0005518128")

        assert calls["count"] == 1
        assert first.name == second.name

    def test_network_error_soft_passes_and_is_not_cached(self):
        validator, calls = make_validator(exc=httpx.ConnectError("connection refused"))

        first = validator.validate("IT0005518128")
        validator.validate("IT0005518128")

        assert first.is_valid is True  # soft-pass: never block on outage
        assert "unavailable" in first.message
        assert calls["count"] == 2  # not cached — retried next time

    def test_rate_limit_soft_passes_and_is_not_cached(self):
        validator, calls = make_validator(status_code=429)

        first = validator.validate("IT0005518128")

        assert first.is_valid is True
        assert "rate" in first.message.lower()
        assert calls["count"] == 1  # failed once; uncached would re-request

    def test_http_error_status_soft_passes(self):
        validator, calls = make_validator(status_code=500)

        result = validator.validate("IT0005518128")

        assert result.is_valid is True
        assert calls["count"] == 1

    def test_ticker_short_circuits_without_http(self):
        validator, calls = make_validator(payload=[])

        results = validator.validate_many(["AAPL"], identifier_type="TICKER")

        assert calls["count"] == 0
        assert results["AAPL"].is_valid is True
        assert "ISINs only" in results["AAPL"].message

    def test_validate_single_returns_result(self):
        validator, _ = make_validator(payload=[mapping_entry()])

        result = validator.validate("it0005518128")

        assert isinstance(result, ValidationResult)
        assert result.security_type == "bond"

    def test_unexpected_entry_shape_soft_passes(self):
        validator, _ = make_validator(payload=[{"something": "else"}])

        result = validator.validate("IT0005518128")

        assert result.is_valid is True
        assert "Unexpected" in result.message
