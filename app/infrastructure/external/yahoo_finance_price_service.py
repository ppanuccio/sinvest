"""Yahoo Finance Price Service - fetches current prices from Yahoo Finance.

Uses the yfinance library (https://github.com/ranaroussi/yfinance) which handles
Yahoo Finance's cookie consent, crumb token, and rate limiting requirements
that the raw HTTP API rejects with 429 errors.
"""

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import yfinance as yf


class YahooFinanceError(Exception):
    """Exception raised when Yahoo Finance API returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class PriceQuote:
    """Domain model for a price quote."""

    symbol: str
    price: Decimal
    currency: str
    timestamp: int
    short_name: Optional[str] = None
    long_name: Optional[str] = None


class YahooFinancePriceService:
    """
    Service to fetch current prices from Yahoo Finance.

    Wraps the yfinance library to provide an async interface with
    retry logic and proper error handling.
    """

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def _run_in_thread(self, func, *args, **kwargs):
        """Run a synchronous function in a thread pool."""
        return await asyncio.to_thread(func, *args, **kwargs)

    def _extract_price_quote(self, ticker: yf.Ticker, symbol: str) -> Optional[PriceQuote]:
        """Extract a PriceQuote from a yfinance Ticker object."""
        try:
            info = ticker.info
            if not info or info.get("regularMarketPrice") is None:
                return None

            price = info["regularMarketPrice"]
            return PriceQuote(
                symbol=symbol,
                price=Decimal(str(price)),
                currency=info.get("currency", "USD"),
                timestamp=info.get("regularMarketTime", 0),
                short_name=info.get("shortName"),
                long_name=info.get("longName"),
            )
        except Exception as e:
            raise YahooFinanceError(f"Failed to parse price data for {symbol}: {e}")

    async def fetch_price(self, symbol: str) -> PriceQuote:
        """
        Fetch current price for a single symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL", "MSFT", "VWCE.AS")

        Returns:
            PriceQuote with current price information

        Raises:
            YahooFinanceError: If the API returns an error or no data found
        """
        quotes = await self.fetch_prices([symbol])
        if not quotes:
            raise YahooFinanceError(f"No price data found for symbol: {symbol}")
        return quotes[0]

    async def fetch_prices(self, symbols: list[str]) -> list[PriceQuote]:
        """
        Fetch current prices for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            List of PriceQuote objects (may be shorter than input if some symbols fail)
        """
        if not symbols:
            return []

        last_error = None
        for attempt in range(self.max_retries):
            try:
                quotes = []
                for symbol in symbols:
                    try:
                        ticker = await self._run_in_thread(yf.Ticker, symbol)
                        info = await self._run_in_thread(lambda: ticker.info)

                        if not info or info.get("regularMarketPrice") is None:
                            continue

                        price = info["regularMarketPrice"]
                        quotes.append(
                            PriceQuote(
                                symbol=symbol,
                                price=Decimal(str(price)),
                                currency=info.get("currency", "USD"),
                                timestamp=info.get("regularMarketTime", 0),
                                short_name=info.get("shortName"),
                                long_name=info.get("longName"),
                            )
                        )
                    except Exception as e:
                        # Log individual symbol failures but continue
                        last_error = YahooFinanceError(f"Failed to fetch {symbol}: {e}")
                        continue

                if quotes:
                    return quotes

                raise last_error or YahooFinanceError("No price data returned for any symbol")

            except YahooFinanceError:
                raise
            except Exception as e:
                last_error = YahooFinanceError(f"Unexpected error: {e}")

            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        raise last_error or YahooFinanceError("Failed to fetch prices after retries")

    async def resolve_ticker(self, symbol: str) -> dict:
        """
        Check if a ticker is ambiguous by searching Yahoo Finance for exchange variants.

        Uses yfinance.Search to find all exchange-listed variants of a symbol.
        Returns a dict with:
          - exact: True if the bare symbol has price data (unambiguous)
          - suggestions: list of {symbol, shortName, exchange, typeDisp} for exchange variants
          - message: human-readable description

        Args:
            symbol: Stock symbol to check (e.g., "XEON", "AAPL")

        Returns:
            dict with resolution info
        """
        if not symbol or "." in symbol:
            # Already has an exchange suffix — just try to validate it
            try:
                ticker = await self._run_in_thread(yf.Ticker, symbol)
                info = await self._run_in_thread(lambda: ticker.info)
                has_price = info and info.get("regularMarketPrice") is not None
                if has_price:
                    return {
                        "exact": True,
                        "suggestions": [],
                        "message": f"{symbol} is valid and has price data.",
                    }
            except Exception:
                pass
            return {
                "exact": False,
                "suggestions": [],
                "message": f"{symbol} could not be found on Yahoo Finance.",
            }

        # Search for the bare symbol to find exchange variants
        try:
            search = await self._run_in_thread(yf.Search, symbol, 10)
            quotes = search.quotes or []
        except Exception:
            quotes = []

        # Filter to only variants that start with the exact symbol + "."
        prefix = f"{symbol}."
        # Also look for the exact symbol match (no suffix)
        suggestions = []
        exact_match = False

        for q in quotes:
            sym = q.get("symbol", "")
            if sym == symbol:
                exact_match = True
            elif sym.startswith(prefix):
                suggestions.append({
                    "symbol": sym,
                    "shortName": q.get("shortname") or q.get("longname") or "",
                    "exchange": q.get("exchDisp", ""),
                    "typeDisp": q.get("typeDisp", ""),
                })

        # Deduplicate by symbol
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s["symbol"] not in seen:
                seen.add(s["symbol"])
                unique_suggestions.append(s)

        # If the bare symbol already has price data, it's not really ambiguous
        if exact_match:
            try:
                ticker = await self._run_in_thread(yf.Ticker, symbol)
                info = await self._run_in_thread(lambda: ticker.info)
                if info and info.get("regularMarketPrice") is not None:
                    return {
                        "exact": True,
                        "suggestions": [],
                        "message": f"{symbol} is valid and has price data.",
                    }
            except Exception:
                pass

        if unique_suggestions:
            exchanges = ", ".join(
                f"{s['symbol']} ({s['exchange']})" for s in unique_suggestions[:5]
            )
            return {
                "exact": False,
                "suggestions": unique_suggestions,
                "message": (
                    f'"{symbol}" is ambiguous. Try one of: {exchanges}'
                ),
            }

        # No results at all
        return {
            "exact": False,
            "suggestions": [],
            "message": f"No exchange listings found for '{symbol}'.",
        }

    async def get_exchange_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """
        Get the exchange rate from one currency to another using Yahoo Finance.

        Uses Yahoo Finance forex pairs (e.g., EURUSD=X for EUR→USD).
        Results are cached in memory for the lifetime of this service instance.

        Args:
            from_currency: Source currency code (e.g., "EUR", "USD")
            to_currency: Target currency code (e.g., "USD", "EUR")

        Returns:
            Decimal exchange rate (multiply source amount by this to get target)

        Raises:
            YahooFinanceError: If the rate cannot be fetched
        """
        if from_currency == to_currency:
            return Decimal("1")

        # Check cache
        cache_key = f"{from_currency}→{to_currency}"
        if hasattr(self, "_rate_cache") and cache_key in self._rate_cache:
            return self._rate_cache[cache_key]

        symbol = f"{from_currency}{to_currency}=X"
        try:
            ticker = await self._run_in_thread(yf.Ticker, symbol)
            info = await self._run_in_thread(lambda: ticker.info)
            rate = info.get("regularMarketPrice") or info.get("previousClose")
            if rate is None:
                raise YahooFinanceError(
                    f"Could not get exchange rate for {from_currency}→{to_currency}"
                )
            result = Decimal(str(rate))

            # Cache the result
            if not hasattr(self, "_rate_cache"):
                self._rate_cache = {}
            self._rate_cache[cache_key] = result

            return result
        except YahooFinanceError:
            raise
        except Exception as e:
            raise YahooFinanceError(
                f"Failed to fetch exchange rate for {from_currency}→{to_currency}: {e}"
            )

    async def close(self) -> None:
        """No-op for compatibility with context manager usage."""
        pass

    async def __aenter__(self) -> "YahooFinancePriceService":
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()