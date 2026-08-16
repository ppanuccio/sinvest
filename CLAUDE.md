# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

**sinvest** is a personal investment portfolio manager: a Python backend with a plain-HTML/vanilla-JS frontend, organized in strict Clean/Hexagonal Architecture. Users own portfolios, portfolios contain investments, investments are identified by ISIN or TICKER and have multiple transactions (amount, quantity, broker, date, currency) plus a recorded price history.

## Commands

```bash
# Run the full test suite (pytest is configured with --cov in pyproject.toml)
python -m pytest tests/ -v --tb=short

# Run a single test file or test
python -m pytest tests/unit/domain/test_value_objects.py -v
python -m pytest tests/unit/application/test_portfolio_analytics_use_cases.py::test_x -v

# Run the HTTP API (serves the UI at /ui) — see .claude/settings.local.json
uvicorn app.infrastructure.http_api:app --host 127.0.0.1 --port 8765

# CLI entrypoint (works standalone; inserts repo root into sys.path itself)
python app/infrastructure/cli.py --help

# Lint/format (dev deps)
flake8 app/ tests/
black --check app/
mypy app/
```

## Architecture

Dependency rule: **domain → application → infrastructure** — nothing outside can import inward. Adapters (FastAPI, CLI, JSON files, yfinance) all depend on application interfaces; the domain layer is framework-agnostic.

- **`app/domain/`** — entities (`User`, `Portfolio`, `Investment`, `Transaction`, `PriceHistory`), **frozen `value_objects`** (`Identifier`, `Money`, `Quantity`, `Yield`, `InvestmentType`), exception hierarchy, repository *interfaces* (`app/domain/repositories/`), and stateless calculation services (`investment_calculation_service.py`, `portfolio_calculation_service.py`, `validation_service.py`).
- **`app/application/`** — orchestration use cases (`use_cases/`), DTOs, and security abstractions (`PasswordHasher`, `TokenService`). Use cases depend only on repository interfaces and value objects.
- **`app/infrastructure/`** — concrete adapters: `http_api.py` (FastAPI app), `cli.py`, `file_based_repositories.py` (JSON persistence in `data/`), `in_memory_repositories.py` (test doubles), `security.py` (PBKDF2 + HMAC token), `external/yahoo_finance_price_service.py` (price/forex fetching), and `ui/` (static frontend).

## Money & calculations rules

- All money is `Decimal` via the `Money` value object; formats use `Decimal(str(...))`, never floats.
- Investment total quantity = sum of transaction quantities. Investment **value** = `(current_price × total_quantity) − total_invested` (a "net" value), NOT just price × quantity. Yield is derived from that net value against the initial amount.
- Transactions and price quotes carry a currency. Analytics endpoints take a `reference_currency` (default USD) and convert every monetary value into it. Exchange rates come from `YahooFinanceService.get_exchange_rate()` (cached in-memory per instance) and are passed down as a `rates: dict[str, Decimal]` — `calculated_amount_helpers` (`_convert_amount`, `convert_to`) must be used consistently.
- **Gotcha (fixed twice)**: any `Money` coming from transactions (`initial_amount`, etc.) must be converted to the reference currency *before* it reaches methods that compare currencies (`calculate_yield`), or the broad `except Exception` in analytics silently nulls the VALUE/GAIN fields. When converting to a reference currency, use `_convert_amount` helper.
- `calculate_total_invested_amount` returns `Money(Decimal("0"))` when there are no transactions; `calculate_initial_amount` returns `None` instead.

### Yahoo Finance

The external price provider is `app/infrastructure/external/yahoo_finance_price_service.py`, which wraps the `yfinance` library (`pip` v1.5+) via `asyncio.to_thread()` (async-friendliness). Prior versions used a raw httpx-based Yahoo v7 API that 429ed. Notable behavior:

- Uses `ticker.info["regularMarketPrice"]` — no `symbol` filtering; the service handles cookie/consent/crumb internally.
- `resolve_ticker(symbol)` uses `yfinance.Search` to detect ambiguous tickers that need an exchange suffix (e.g. `XEON` → `XEON.MIL`); returns `{exact, suggestions, message}`.
- `get_exchange_rate(from, to)` uses `from+to=X` forex symbols (e.g. `EURUSD=X`) and caches in `self._rate_cache`.
- `fetch_prices` retries up to `max_retries`, skips individual symbol failures, and raises `YahooFinanceError` if nothing returns.
- When currency conversion fails, `FetchPriceUseCases.fetch_and_store_current_price` raises `YahooFinanceError` which the API maps to 502 Bad Gateway.

## API & auth

- FastAPI app in `app/infrastructure/http_api.py` mounts the static UI at `/ui` and redirects `/` → `/ui/`. 
- All routes under `/users/{user_id}/...` require a Bearer token; `get_authenticated_user_id` + `require_route_user` enforces that route `user_id` matches the token's `sub`. Public endpoints: `/health`, `/ticker/check`.
- Auth: PBKDF2-HMAC password hashing (`PBKDF2PasswordHasher`, 120k iters), stateless signed tokens (`HMACTokenService`, HS256-esque but hand-rolled base64url), expiry 8h, secret from `SINVEST_AUTH_SECRET` env (falls back to `sinvest-development-secret`).
- Domain errors map to HTTP: `EntityNotFoundException`→404, `AuthenticationFailedException`→401, `UnauthorizedException`→403, `DuplicateUserException`→409, else 400, via the single `DomainException` exception handler.
- Response models are Pydantic `BaseModel` with `model_config = {"from_attributes": True}`.

## Persistence

- `FileBasedRepo` subclasses in `file_based_repositories.py` read/write JSON (`data/*.json`), using a standard `__init__(self, file_path="data/users.json")` per repo and `data/` is gitignored except `data/credentials.json` (tracked).
- JSON codec is custom: `JSONEncoder`/`_decode_value` round-trips `Decimal` (as string), `datetime` (isoformat), and value objects (`Identifier`, `Money`, `Quantity`, `InvestmentType`) via marker keys (`__identifier__`, `__money__`, `__quantity__`).

## UI

Static, vanilla HTML+CSS+JS in `app/infrastructure/ui/` (`index.html`, `app.js`). No build step, no framework. Auth token stored in `localStorage.AUTH_STORAGE_KEY` (key `'sinvest.auth'`). `_getRoute` style logic in `app.js` hits the API over fetch.

## Testing

- Test sessions use in-memory repository stubs (`tests/infrastructure/in_memory_repositories.py`); file-backed repos are covered under `tests/infrastructure/test_file_based_repositories.py`.
- Test suite is coerced to `--cov=app` automatically via pyproject `addopts`; the `htmlcov/` output dir is gitignored.
- pytest config: `asyncio_mode = "auto"` so async tests need no marks; `testpaths = ["tests"]`.