"""Yahoo Finance Price Service - fetches current prices from Yahoo Finance API."""

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import httpx
from pydantic import BaseModel, Field


class YahooFinanceError(Exception):
    """Exception raised when Yahoo Finance API returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class YahooFinanceQuoteResponse(BaseModel):
    """Response model for Yahoo Finance quote API."""

    symbol: str
    regularMarketPrice: Optional[float] = Field(None, alias="regularMarketPrice")
    regularMarketTime: Optional[int] = Field(None, alias="regularMarketTime")
    currency: Optional[str] = None
    shortName: Optional[str] = Field(None, alias="shortName")
    longName: Optional[str] = Field(None, alias="longName")

    class Config:
        populate_by_name = True


class YahooFinanceResult(BaseModel):
    """Individual result from Yahoo Finance API."""

    symbol: str
    regularMarketPrice: Optional[float] = None
    regularMarketTime: Optional[int] = None
    currency: Optional[str] = None
    shortName: Optional[str] = None
    longName: Optional[str] = None


class YahooFinanceResponse(BaseModel):
    """Top-level response from Yahoo Finance API."""

    quoteResponse: "YahooFinanceQuoteResponse" = Field(alias="quoteResponse")

    class Config:
        populate_by_name = True


class YahooFinanceQuoteResponse(BaseModel):
    """Quote response container."""

    result: list[YahooFinanceResult] = []
    error: Optional[dict] = None


YahooFinanceResponse.model_rebuild()


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
    Service to fetch current prices from Yahoo Finance API.

    Uses the Yahoo Finance v8 finance API which provides real-time quotes.
    """

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
    QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"User-Agent": self.USER_AGENT},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "YahooFinancePriceService":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

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

        client = await self._get_client()
        params = {"symbols": ",".join(symbols)}

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await client.get(self.QUOTE_URL, params=params)
                response.raise_for_status()
                data = response.json()

                quote_response = YahooFinanceResponse.model_validate(
                    {"quoteResponse": data}
                )

                if quote_response.quoteResponse.error:
                    raise YahooFinanceError(
                        f"Yahoo Finance API error: {quote_response.quoteResponse.error}",
                        status_code=response.status_code,
                    )

                results = quote_response.quoteResponse.result
                quotes = []

                for result in results:
                    if result.regularMarketPrice is not None:
                        quote = PriceQuote(
                            symbol=result.symbol,
                            price=Decimal(str(result.regularMarketPrice)),
                            currency=result.currency or "USD",
                            timestamp=result.regularMarketTime or 0,
                            short_name=result.shortName,
                            long_name=result.longName,
                        )
                        quotes.append(quote)

                return quotes

            except httpx.HTTPStatusError as e:
                last_error = YahooFinanceError(
                    f"HTTP error: {e.response.status_code}",
                    status_code=e.response.status_code,
                )
            except httpx.RequestError as e:
                last_error = YahooFinanceError(f"Request error: {str(e)}")
            except Exception as e:
                last_error = YahooFinanceError(f"Unexpected error: {str(e)}")

            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        raise last_error or YahooFinanceError("Failed to fetch prices after retries")


async def fetch_price(symbol: str) -> PriceQuote:
    """
    Convenience function to fetch a single price.

    Creates a service instance, fetches the price, and closes the client.
    """
    async with YahooFinancePriceService() as service:
        return await service.fetch_price(symbol)


async def fetch_prices(symbols: list[str]) -> list[PriceQuote]:
    """
    Convenience function to fetch multiple prices.

    Creates a service instance, fetches the prices, and closes the client.
    """
    async with YahooFinancePriceService() as service:
        return await service.fetch_prices(symbols)