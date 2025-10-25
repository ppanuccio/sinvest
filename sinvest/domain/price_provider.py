from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Protocol


class MarketPriceProvider(ABC):
    """Abstract interface to fetch market prices for symbols.

    This keeps domain code independent from the concrete data source
    (yfinance, external API, cached provider, etc.).
    """

    @abstractmethod
    def get_price(self, symbol: str) -> float:
        """Return last price for given symbol or 0.0 on failure."""
        raise NotImplementedError()


class YFinancePriceProvider(MarketPriceProvider):
    """Production provider using yfinance."""

    def __init__(self, yf_module=None):
        # allow injection of yf for easier testing
        import yfinance as yf
        self._yf = yf if yf_module is None else yf_module

    def get_price(self, symbol: str) -> float:
        try:
            ticker = self._yf.Ticker(symbol)
            series = ticker.history(period="1d")["Close"]
            return float(series.iloc[-1])
        except Exception:
            return 0.0


class MockPriceProvider(MarketPriceProvider):
    """Test provider: returns a fixed price or mapping supplied at construction."""

    def __init__(self, mapping: dict[str, float] | None = None, default: float = 0.0):
        self.mapping = mapping or {}
        self.default = default

    def get_price(self, symbol: str) -> float:
        return float(self.mapping.get(symbol, self.default))
