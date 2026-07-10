from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from app.application.dto.auth_dto import LoginDTO
from app.application.dto.investment_dto import CreateInvestmentDTO
from app.application.dto.portfolio_dto import CreatePortfolioDTO
from app.application.dto.transaction_dto import CreateTransactionDTO
from app.application.dto.user_dto import CreateUserDTO
from app.application.use_cases.authentication_use_cases import AuthenticationUseCases
from app.application.use_cases.investment_use_cases import InvestmentUseCases
from app.application.use_cases.portfolio_use_cases import PortfolioUseCases
from app.application.use_cases.transaction_use_cases import TransactionUseCases
from app.application.use_cases.user_use_cases import UserUseCases
from app.application.use_cases.portfolio_analytics_use_cases import (
    PortfolioAnalyticsUseCases,
)
from app.application.use_cases.price_history_use_cases import PriceHistoryUseCases
from app.application.use_cases.fetch_price_use_cases import (
    FetchPriceUseCases,
    YahooFinanceError,
)
from app.domain.exceptions import (
    AuthenticationFailedException,
    DuplicateUserException,
    DomainException,
    EntityNotFoundException,
    UnauthorizedException,
)
from app.infrastructure.file_based_repositories import (
    FileBasedCredentialRepository,
    FileBasedInvestmentRepository,
    FileBasedPriceHistoryRepository,
    FileBasedPortfolioRepository,
    FileBasedTransactionRepository,
    FileBasedUserRepository,
)
from app.infrastructure.security import HMACTokenService, PBKDF2PasswordHasher
from app.infrastructure.external.yahoo_finance_price_service import (
    YahooFinancePriceService,
)

app = FastAPI(title="sinvest HTTP API", version="0.1.0")

# Mount the simple static UI at /ui if available
_ui_path = Path(__file__).resolve().parent / "ui"
if _ui_path.exists():
    app.mount("/ui", StaticFiles(directory=str(_ui_path), html=True), name="ui")


@app.get("/")
async def _root_redirect():
    return RedirectResponse(url="/ui/")

# Instantiate persistent repositories for HTTP-backed interaction.
user_repository = FileBasedUserRepository()
credential_repository = FileBasedCredentialRepository()
portfolio_repository = FileBasedPortfolioRepository()
investment_repository = FileBasedInvestmentRepository()
transaction_repository = FileBasedTransactionRepository()
price_history_repository = FileBasedPriceHistoryRepository()
password_hasher = PBKDF2PasswordHasher()
token_service = HMACTokenService()

user_use_cases = UserUseCases(user_repository)
authentication_use_cases = AuthenticationUseCases(
    user_use_cases,
    user_repository,
    credential_repository,
    password_hasher,
    token_service,
)
portfolio_use_cases = PortfolioUseCases(portfolio_repository)
investment_use_cases = InvestmentUseCases(
    investment_repository,
    portfolio_repository,
    transaction_repository,
    price_history_repository,
)
transaction_use_cases = TransactionUseCases(
    transaction_repository, investment_repository, portfolio_repository
)

portfolio_analytics_use_cases = PortfolioAnalyticsUseCases(
    portfolio_repository,
    investment_repository,
    transaction_repository,
    price_history_repository,
)

price_history_use_cases = PriceHistoryUseCases(
    price_history_repository,
    investment_repository,
    portfolio_repository,
)

fetch_price_use_cases = FetchPriceUseCases(
    price_history_repository,
    investment_repository,
    portfolio_repository,
)


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class CreatePortfolioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class CreateInvestmentRequest(BaseModel):
    identifier: str = Field(..., min_length=1, max_length=50)
    identifier_type: str = Field(..., pattern="^(ISIN|TICKER)$")
    type: str = Field(
        ...,
        pattern="^(stock|bond|etf|crypto|mutual_fund|commodity|other)$",
    )


class CreateTransactionRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0)
    broker: str = Field(..., min_length=1, max_length=100)
    date: datetime
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$")


class CreatePriceHistoryRequest(BaseModel):
    price: Decimal = Field(..., gt=0)
    date: datetime


class PriceHistoryResponseModel(BaseModel):
    id: str
    investment_id: str
    price: Decimal
    date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class UserResponseModel(BaseModel):
    id: str
    username: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class AuthTokenResponseModel(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str

    model_config = {"from_attributes": True}


class PortfolioResponseModel(BaseModel):
    id: str
    user_id: str
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class InvestmentResponseModel(BaseModel):
    id: str
    portfolio_id: str
    identifier: str
    identifier_type: str
    type: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class TransactionResponseModel(BaseModel):
    id: str
    investment_id: str
    amount: Decimal
    quantity: Decimal
    broker: str
    date: datetime
    created_at: datetime
    updated_at: datetime
    currency: str = "USD"

    model_config = {"from_attributes": True}


@app.exception_handler(DomainException)
async def domain_exception_handler(request, exc: DomainException):
    if isinstance(exc, EntityNotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, AuthenticationFailedException):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, UnauthorizedException):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, DuplicateUserException):
        status_code = status.HTTP_409_CONFLICT
    else:
        status_code = status.HTTP_400_BAD_REQUEST
    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc)},
    )


bearer_scheme = HTTPBearer(auto_error=False)


async def get_authenticated_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return authentication_use_cases.authenticate_token(
            credentials.credentials
        )
    except AuthenticationFailedException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_route_user(
    user_id: str,
    authenticated_user_id: str = Depends(get_authenticated_user_id),
) -> str:
    if authenticated_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user does not match route user",
        )
    return authenticated_user_id


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.get("/ticker/check")
async def check_ticker(symbol: str):
    """
    Check if a ticker is ambiguous by searching Yahoo Finance for exchange variants.

    Returns a JSON object with:
      - exact: True if the bare symbol has price data (unambiguous)
      - suggestions: list of {symbol, shortName, exchange, typeDisp} for exchange variants
      - message: human-readable description

    This is a public endpoint (no auth required) used by the UI to validate tickers
    before the user adds an investment.
    """
    svc = YahooFinancePriceService()
    try:
        result = await svc.resolve_ticker(symbol.upper().strip())
        return result
    except Exception as e:
        return {"exact": False, "suggestions": [], "message": str(e)}


def _encode_value(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _encode_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_encode_value(i) for i in v]
    return v


@app.get(
    "/users/{user_id}/portfolios/{portfolio_id}/analytics",
)
async def get_portfolio_analytics(
    user_id: str,
    portfolio_id: str,
    reference_currency: str = "USD",
    authenticated_user_id: str = Depends(require_route_user),
):
    try:
        analytics = await portfolio_analytics_use_cases.get_portfolio_analytics(
            portfolio_id, user_id, reference_currency
        )
        payload = asdict(analytics)
        return JSONResponse(content=_encode_value(payload))
    except YahooFinanceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@app.post("/users", response_model=UserResponseModel, status_code=status.HTTP_201_CREATED)
async def create_user(request: CreateUserRequest) -> UserResponseModel:
    dto = CreateUserDTO(
        username=request.username,
        email=request.email,
        password=request.password,
    )
    user = authentication_use_cases.register_user(dto)
    return UserResponseModel.model_validate(user)


@app.post("/auth/login", response_model=AuthTokenResponseModel)
async def login(request: LoginRequest) -> AuthTokenResponseModel:
    dto = LoginDTO(username=request.username, password=request.password)
    token = authentication_use_cases.login(dto)
    return AuthTokenResponseModel.model_validate(token)


@app.get("/users/{user_id}", response_model=UserResponseModel)
async def get_user(
    user_id: str,
    authenticated_user_id: str = Depends(require_route_user),
) -> UserResponseModel:
    user = user_use_cases.get_user(user_id)
    return UserResponseModel.model_validate(user)


@app.post(
    "/users/{user_id}/portfolios",
    response_model=PortfolioResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_portfolio(
    user_id: str,
    request: CreatePortfolioRequest,
    authenticated_user_id: str = Depends(require_route_user),
) -> PortfolioResponseModel:
    dto = CreatePortfolioDTO(
        user_id=user_id,
        name=request.name,
        description=request.description,
    )
    portfolio = portfolio_use_cases.create_portfolio(user_id, dto)
    return PortfolioResponseModel.model_validate(portfolio)


@app.get("/users/{user_id}/portfolios", response_model=List[PortfolioResponseModel])
async def list_portfolios(
    user_id: str,
    authenticated_user_id: str = Depends(require_route_user),
) -> List[PortfolioResponseModel]:
    portfolios = portfolio_use_cases.list_portfolios(user_id)
    return [PortfolioResponseModel.model_validate(portfolio) for portfolio in portfolios]


@app.get("/users/{user_id}/portfolios/{portfolio_id}", response_model=PortfolioResponseModel)
async def get_portfolio(
    user_id: str,
    portfolio_id: str,
    authenticated_user_id: str = Depends(require_route_user),
) -> PortfolioResponseModel:
    portfolio = portfolio_use_cases.get_portfolio(portfolio_id, user_id)
    return PortfolioResponseModel.model_validate(portfolio)


@app.post(
    "/users/{user_id}/portfolios/{portfolio_id}/investments",
    response_model=InvestmentResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_investment(
    user_id: str,
    portfolio_id: str,
    request: CreateInvestmentRequest,
    authenticated_user_id: str = Depends(require_route_user),
) -> InvestmentResponseModel:
    dto = CreateInvestmentDTO(
        portfolio_id=portfolio_id,
        identifier=request.identifier,
        identifier_type=request.identifier_type,
        type=request.type,
    )
    investment = investment_use_cases.create_investment(user_id, dto)
    return InvestmentResponseModel.model_validate(investment)


@app.delete(
    "/users/{user_id}/investments/{investment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_investment(
    user_id: str,
    investment_id: str,
    authenticated_user_id: str = Depends(require_route_user),
) -> None:
    """Delete an investment."""
    investment_use_cases.delete_investment(investment_id, user_id)


@app.get(
    "/users/{user_id}/portfolios/{portfolio_id}/investments",
    response_model=List[InvestmentResponseModel],
)
async def list_investments(
    user_id: str,
    portfolio_id: str,
    authenticated_user_id: str = Depends(require_route_user),
) -> List[InvestmentResponseModel]:
    investments = investment_use_cases.list_investments(portfolio_id, user_id)
    return [InvestmentResponseModel.model_validate(investment) for investment in investments]


@app.post(
    "/users/{user_id}/investments/{investment_id}/transactions",
    response_model=TransactionResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    user_id: str,
    investment_id: str,
    request: CreateTransactionRequest,
    authenticated_user_id: str = Depends(require_route_user),
) -> TransactionResponseModel:
    dto = CreateTransactionDTO(
        investment_id=investment_id,
        amount=request.amount,
        quantity=request.quantity,
        broker=request.broker,
        date=request.date,
        currency=request.currency,
    )
    transaction = transaction_use_cases.create_transaction(user_id, dto)
    return TransactionResponseModel.model_validate(transaction)


@app.get(
    "/users/{user_id}/investments/{investment_id}/transactions",
    response_model=List[TransactionResponseModel],
)
async def list_transactions(
    user_id: str,
    investment_id: str,
    authenticated_user_id: str = Depends(require_route_user),
) -> List[TransactionResponseModel]:
    transactions = transaction_use_cases.list_transactions(investment_id, user_id)
    return [TransactionResponseModel.model_validate(transaction) for transaction in transactions]


@app.post(
    "/users/{user_id}/investments/{investment_id}/prices",
    response_model=PriceHistoryResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def record_price(
    user_id: str,
    investment_id: str,
    request: CreatePriceHistoryRequest,
    authenticated_user_id: str = Depends(require_route_user),
) -> PriceHistoryResponseModel:
    from app.application.dto.price_history_dto import CreatePriceHistoryDTO

    dto = CreatePriceHistoryDTO(
        investment_id=investment_id,
        price=request.price,
        date=request.date,
    )
    price_history = price_history_use_cases.record_price(user_id, dto)
    return PriceHistoryResponseModel.model_validate(price_history)


@app.get(
    "/users/{user_id}/investments/{investment_id}/prices/latest",
    response_model=PriceHistoryResponseModel,
)
async def get_latest_price(
    user_id: str,
    investment_id: str,
    authenticated_user_id: str = Depends(require_route_user),
) -> PriceHistoryResponseModel:
    price_history = price_history_use_cases.get_latest_price(investment_id, user_id)
    if not price_history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No price history found for this investment",
        )
    return PriceHistoryResponseModel.model_validate(price_history)


@app.get(
    "/users/{user_id}/investments/{investment_id}/prices",
    response_model=List[PriceHistoryResponseModel],
)
async def list_prices(
    user_id: str,
    investment_id: str,
    authenticated_user_id: str = Depends(require_route_user),
) -> List[PriceHistoryResponseModel]:
    prices = price_history_use_cases.list_prices(investment_id, user_id)
    return [PriceHistoryResponseModel.model_validate(p) for p in prices]


@app.get(
    "/users/{user_id}/investments/{investment_id}/prices/range",
    response_model=List[PriceHistoryResponseModel],
)
async def list_prices_by_date_range(
    user_id: str,
    investment_id: str,
    from_date: datetime,
    to_date: datetime,
    authenticated_user_id: str = Depends(require_route_user),
) -> List[PriceHistoryResponseModel]:
    prices = price_history_use_cases.list_prices_by_date_range(
        investment_id, user_id, from_date, to_date
    )
    return [PriceHistoryResponseModel.model_validate(p) for p in prices]


@app.post(
    "/users/{user_id}/investments/{investment_id}/prices/fetch",
    response_model=PriceHistoryResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def fetch_and_store_current_price(
    user_id: str,
    investment_id: str,
    authenticated_user_id: str = Depends(require_route_user),
) -> PriceHistoryResponseModel:
    """
    Fetch current price from Yahoo Finance and store it in price history.

    This endpoint:
    1. Verifies the investment exists and belongs to the user
    2. Fetches the current market price from Yahoo Finance
    3. Stores the price in the price history
    4. Returns the stored price record

    Note: Currently only supports investments with TICKER identifier type.
    ISIN identifiers are not directly supported by Yahoo Finance API.
    """
    try:
        price_history = await fetch_price_use_cases.fetch_and_store_current_price(
            user_id, investment_id
        )
        return PriceHistoryResponseModel.model_validate(price_history)
    except YahooFinanceError as e:
        detail = f"Failed to fetch price from Yahoo Finance: {e}"
        # Add a hint for European tickers that need an exchange suffix
        if "No price data" in str(e) or "no data" in str(e).lower():
            detail += " For European ETFs/stocks, try adding an exchange suffix (.DE, .MI, .AS, .L, .PA, .SW)."
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )


@app.post(
    "/users/{user_id}/investments/prices/fetch-batch",
    response_model=List[PriceHistoryResponseModel],
    status_code=status.HTTP_201_CREATED,
)
async def fetch_and_store_multiple_prices(
    user_id: str,
    investment_ids: List[str],
    authenticated_user_id: str = Depends(require_route_user),
) -> List[PriceHistoryResponseModel]:
    """
    Fetch current prices for multiple investments from Yahoo Finance and store them.

    This endpoint:
    1. Verifies all investments exist and belong to the user
    2. Fetches current market prices from Yahoo Finance in batch
    3. Stores the prices in the price history
    4. Returns the stored price records

    Note: Only investments with TICKER identifier type are supported.
    """
    try:
        price_histories = await fetch_price_use_cases.fetch_and_store_multiple_prices(
            user_id, investment_ids
        )
        return [PriceHistoryResponseModel.model_validate(p) for p in price_histories]
    except YahooFinanceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch prices from Yahoo Finance: {e}",
        )
