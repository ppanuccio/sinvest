# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

**sinvest** is a personal investment portfolio manager: a Python backend with a plain-HTML/vanilla-JS frontend, organized in strict Clean/Hexagonal Architecture. Users own portfolios, portfolios contain investments, investments are identified by ISIN or TICKER and have multiple transactions (amount, quantity, broker, date, currency, kind — `buy` or `coupon`) plus a recorded price history.

## Commands

```bash
# Setup: install dependencies and create .venv (from uv.lock)
uv sync

# Add a dependency (for a dev dependency: uv add --dev <pkg>)
uv add <package>

# Run the full test suite (pytest is configured with --cov in pyproject.toml)
uv run pytest tests/ -v --tb=short

# Run a single test file or test
uv run pytest tests/unit/domain/test_value_objects.py -v
uv run pytest tests/unit/application/test_portfolio_analytics_use_cases.py::test_x -v

# Run the HTTP API (serves the UI at /ui) — see .claude/settings.local.json
uv run uvicorn app.infrastructure.http_api:app --host 127.0.0.1 --port 8765

# CLI entrypoint (works standalone; inserts repo root into sys.path itself)
uv run python app/infrastructure/cli.py --help

# Lint/format (dev deps)
uv run flake8 app/ tests/
uv run black --check app/
uv run mypy app/
```

Managed with `uv`. Python is pinned by `.python-version` (3.11); the committed `uv.lock` pins all dependencies. Dev tools live in the `dev` `[dependency-groups]` group and are installed by default. `uv run` executes inside `.venv/` — no shell activation needed.

## Architecture

Dependency rule: **domain → application → infrastructure** — nothing outside can import inward. Adapters (FastAPI, CLI, JSON files, yfinance) all depend on application interfaces; the domain layer is framework-agnostic.

- **`app/domain/`** — entities (`User`, `Portfolio`, `Investment`, `Transaction`, `PriceHistory`, `UserCredential`), **frozen `value_objects`** (`Identifier`, `Money`, `Quantity`, `Yield`, `InvestmentType`), exception hierarchy, repository *interfaces* (`app/domain/repositories/`), and stateless calculation services (`investment_calculation_service.py`, `portfolio_calculation_service.py`, `validation_service.py`).
- **`app/application/`** — orchestration use cases (`use_cases/`), DTOs, and security abstractions (`PasswordHasher`, `TokenService` in `application/security.py`).
- **`app/infrastructure/`** — concrete adapters: `http_api.py` (FastAPI app), `cli.py`, `file_based_repositories.py` (JSON persistence in `data/`), `in_memory_repositories.py` (test doubles), `security.py` (PBKDF2 + HMAC token), `external/yahoo_finance_price_service.py` (price/forex fetching), and `ui/` (static frontend).

**Dead code trap:** `app/domain/services/yahoo_finance_price_service.py` (raw httpx against Yahoo v7/v8 — the old implementation that 429ed) is imported nowhere and has 0% test coverage. The live service is `app/infrastructure/external/yahoo_finance_price_service.py`. Never "fix" the domain copy; delete it when convenient.

## Money & calculations rules

- All money is `Decimal` via the `Money` value object; formats use `Decimal(str(...))`, never floats.
- Investment total quantity = sum of **BUY** transaction quantities; **coupon transactions (`kind="coupon"`) are excluded from quantity and from total invested** — they are income, not acquisition. Coupons are only ever summed by `calculate_total_coupon_income`. Entities created before `kind` existed carry no attribute; always read it defensively (`getattr(tx, "kind", "buy")`), as `_is_coupon` does.
- Investment **value** = `(current_price × total_quantity) − total_invested` (a "net" value), NOT just price × quantity. Yield is derived from that net value against the initial amount.
- **Held-to-maturity bonds** (`Investment.held_to_maturity` + `Investment.face_value`, a per-unit `Money` with its own currency) are valued on a face-value basis with **no live price needed**: `calculate_total_value_bond` = `(face_value × buy_quantity) − total_invested + coupon_income`. Analytics/totals auto-detect them via `is_bond_htm` instead of requiring `price_history`.
- Transactions and price quotes carry a currency. Analytics endpoints take a `reference_currency` (default USD) and convert every monetary value into it. Exchange rates come from `YahooFinanceService.get_exchange_rate()` (cached in-memory per instance) and are passed down as a `rates: dict[str, Decimal]` — `calculated_amount_helpers` (`_convert_amount`, `convert_to`) must be used consistently.
- **Gotcha (fixed twice)**: any `Money` coming from transactions (`initial_amount`, etc.) must be converted to the reference currency *before* it reaches methods that compare currencies (`calculate_yield`), or the broad `except Exception` in analytics silently nulls the VALUE/GAIN fields. When converting to a reference currency, use `_convert_amount` helper.
- `calculate_total_invested_amount` returns `Money(Decimal("0"))` when there are no transactions; `calculate_initial_amount` returns `None` instead.

### Yahoo Finance

The external price provider is `app/infrastructure/external/yahoo_finance_price_service.py`, which wraps the `yfinance` library (`yfinance` ^1.5) via `asyncio.to_thread()` (async-friendliness). Prior versions used a raw httpx-based Yahoo v7 API that 429ed; the dead duplicate still sits at `app/domain/services/yahoo_finance_price_service.py`.

Notable behavior:

- Uses `ticker.info["regularMarketPrice"]` — no `symbol` filtering; the service handles cookie/consent/crumb internally.
- `resolve_ticker(symbol)` uses `yfinance.Search` to detect ambiguous tickers that need an exchange suffix (e.g. `XEON` → `XEON.MIL`); returns `{exact, suggestions, message}` and powers the public `/ticker/check` endpoint.
- `get_exchange_rate(from, to)` uses `from+to=X` forex symbols (e.g. `EURUSD=X`) and caches in `self._rate_cache`.
- `fetch_prices` retries up to `max_retries`, skips individual symbol failures, and raises `YahooFinanceError` if nothing returns.
- When currency conversion fails, `FetchPriceUseCases.fetch_and_store_current_price` raises `YahooFinanceError` which the API maps to 502 Bad Gateway.

## API & auth

- FastAPI app in `app/infrastructure/http_api.py` mounts the static UI at `/ui` and redirects `/` → `/ui/`.
- All routes under `/users/{user_id}/...` require a Bearer token; `get_authenticated_user_id` + `require_route_user` enforces that route `user_id` matches the token's `sub`. Public endpoints: `/health`, `/ticker/check`.
- Auth: PBKDF2-HMAC password hashing (`PBKDF2PasswordHasher`, 120k iters), stateless signed tokens (`HMACTokenService`, HS256-esque but hand-rolled base64url), expiry 8h, secret from `SINVEST_AUTH_SECRET` env (falls back to `sinvest-development-secret`).
- User profile and login credentials are separate: the profile lives in `users.json`, the password hash in a separate `UserCredential` entity persisted to `data/credentials.json` (the only tracked `data/*.json`). Hash format is `pbkdf2_sha256$<iterations>$<salt>$<digest>`; login looks up the credential by username, then the user row by id.
- Domain errors map to HTTP: `EntityNotFoundException`→404, `AuthenticationFailedException`→401, `UnauthorizedException`→403, `DuplicateUserException`→409, else 400, via the single `DomainException` exception handler.
- Deleting an investment cascades to its transactions and price history (the `delete_by_investment` methods on the transaction/price repositories).
- Response models are Pydantic `BaseModel` with `model_config = {"from_attributes": True}`.

## Persistence

- `FileBasedRepo` subclasses in `file_based_repositories.py` read/write JSON (`data/*.json`), using a standard `__init__(self, file_path="data/users.json")` per repo and `data/` is gitignored except `data/credentials.json` (tracked).
- JSON codec is custom: `JSONEncoder`/`_decode_value` round-trips `Decimal` (as string), `datetime` (isoformat), and value objects (`Identifier`, `Money`, `Quantity`) via marker keys (`__identifier__`, `__money__`, `__quantity__`); `InvestmentType` is stored as its plain string value.

## UI

Static, vanilla HTML+CSS+JS in `app/infrastructure/ui/` (`index.html`, `app.js`). No build step, no framework. Auth token stored in `localStorage.AUTH_STORAGE_KEY` (key `'sinvest.auth'`). `_getRoute` style logic in `app.js` hits the API over fetch.

## Testing

- Test sessions use in-memory repository stubs (`tests/infrastructure/in_memory_repositories.py`); file-backed repos are covered under `tests/infrastructure/test_file_based_repositories.py`.
- Test suite is coerced to `--cov=app` automatically via pyproject `addopts`; the `htmlcov/` output dir is gitignored. `cli.py` and the dead domain yahoo service are currently uncovered (0%).
- pytest config: `asyncio_mode = "auto"` so async tests need no marks; `testpaths = ["tests"]`.