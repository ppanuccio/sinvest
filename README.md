# sinvest

A Python-based investment analysis tool for tracking portfolios with multiple currency support.

## Features

- Create and manage investment portfolios
- Track investments (equities, bonds, ETFs)
- Support for multiple currencies
- Real-time price updates via Yahoo Finance
- Portfolio performance tracking with gain/loss calculations

## Installation

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database and apply migrations
flask --app sinvest.app db upgrade
```

## Development Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Apply database migrations:
   ```bash
   flask --app sinvest.app db upgrade
   ```
5. Start the development server:
   ```bash
   flask --app sinvest.app run
   ```

## Database Migrations

This project uses Flask-Migrate (Alembic) for database migrations.

### Creating a New Migration

When you make changes to the database models:

```bash
# Generate a new migration
flask --app sinvest.app db migrate -m "Description of changes"

# Review the generated migration in migrations/versions/
# Then apply it:
flask --app sinvest.app db upgrade
```

### Other Migration Commands

```bash
# Show current migration version
flask --app sinvest.app db current

# Roll back last migration
flask --app sinvest.app db downgrade

# View migration history
flask --app sinvest.app db history
```

## Running Tests

```bash
pytest tests/
```

## License

MIT License