# Availity RPA - Eligibility Check Workflow

Production-style RPA project for automated eligibility checking through the Availity web portal.

## Features

- **Clean Architecture**: Modular design with Page Objects, Repository pattern, and domain models
- **Async Database**: PostgreSQL with SQLAlchemy async ORM and Alembic migrations
- **Type Safety**: Full type hints with Pydantic models
- **Robust Error Handling**: Retry logic with Tenacity, explicit waits, comprehensive error capture
- **Dual Modes**: JSON file-based or database-driven workflow
- **Cross-Platform**: Works on macOS, Linux, and Windows

## Project Structure

```
availity_rpa/
├── env.example               # Environment variables template
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Alternative Python project config
├── alembic.ini              # Alembic configuration
├── alembic/                 # Database migrations
├── config/                  # Application configuration
│   └── settings.py          # Pydantic settings
├── core/                    # Core utilities
│   ├── driver_factory.py    # Selenium WebDriver factory
│   ├── errors.py            # Custom exceptions
│   └── logging.py           # Loguru setup
├── domain/                  # Business domain models
│   └── eligibility_models.py # Pydantic models
├── db/                      # Database layer
│   ├── engine.py            # Async engine & session
│   ├── models.py            # SQLAlchemy ORM models
│   └── repo_eligibility.py  # CRUD operations
├── pages/                   # Page Objects (Selenium)
│   ├── base_page.py         # Base page utilities
│   ├── login_page.py        # Login page
│   ├── dashboard_page.py    # Dashboard navigation
│   └── eligibility_page.py  # Eligibility form & results
├── bots/                    # Bot implementations
│   └── eligibility_bot.py   # Eligibility workflow bot
├── scripts/                 # Executable scripts
│   ├── db_init.py           # Initialize database
│   ├── enqueue_sample.py    # Enqueue test request
│   └── run_eligibility.py   # Main CLI entry point
├── sample/                  # Sample data
│   ├── input_eligibility.json
│   └── output_eligibility.json
└── artifacts/               # Error screenshots & HTML
```

## Quick Start

### 1. Setup Python Environment

```bash
# Create and activate virtual environment
python -m venv .venv

# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or using pyproject.toml:
# pip install -e .
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env with your credentials
# - BASE_URL: Availity portal URL
# - USERNAME/PASSWORD: Your Availity credentials
# - DATABASE_URL: PostgreSQL connection string
```

### 3. Start PostgreSQL

Using Docker:

```bash
docker run --name availity-pg \
  -e POSTGRES_PASSWORD=pass \
  -e POSTGRES_USER=user \
  -e POSTGRES_DB=availity_rpa \
  -p 5432:5432 \
  -d postgres:16
```

Or use an existing PostgreSQL instance and update `DATABASE_URL` in `.env`.

### 4. Initialize Database

```bash
# Create tables and run migrations
python scripts/db_init.py
```

This will:
- Create the database schema
- Enable necessary PostgreSQL extensions (pgcrypto)
- Run all Alembic migrations

### 5. Run Eligibility Check

#### JSON Mode (File-based)

Process a single request from JSON file:

```bash
python scripts/run_eligibility.py \
  --input sample/input_eligibility.json \
  --output sample/output_eligibility.json
```

#### Database Mode (Queue-based)

Enqueue a request and process it:

```bash
# Enqueue a sample request
python scripts/enqueue_sample.py

# Process the next pending request
python scripts/run_eligibility.py --db
```

### Additional Options

```bash
# Run in visible browser mode (not headless)
python scripts/run_eligibility.py --db --no-headless

# JSON mode with visible browser
python scripts/run_eligibility.py \
  --input sample/input_eligibility.json \
  --output sample/output_eligibility.json \
  --no-headless
```

## Database Schema

### Shared Masters

- **payers**: Insurance payer information
- **patients**: Patient demographics
- **patient_payer_enrollments**: Patient-payer relationships with member IDs

### Eligibility Workflow

- **eligibility_requests**: Eligibility check requests with status tracking
- **eligibility_results**: Parsed eligibility results (coverage, deductibles, OOP max)
- **eligibility_benefit_lines**: Detailed benefit lines per result

### Request Statuses

- `PENDING`: Request queued, not yet processed
- `IN_PROGRESS`: Currently being processed by a bot
- `SUCCESS`: Successfully completed and results saved
- `FAILED_PORTAL`: Portal returned an error (e.g., invalid member ID)
- `FAILED_VALIDATION`: Request data validation failed
- `FAILED_TECH`: Technical/unexpected error after retries

## Customization

### Updating Selectors

The Page Objects use **placeholder selectors** marked with `TODO` comments. To use with the real Availity portal:

1. Open the portal in Chrome
2. Inspect elements to find actual selectors
3. Update the following files:
   - `pages/login_page.py` - Username, password, submit button
   - `pages/dashboard_page.py` - Navigation to eligibility section
   - `pages/eligibility_page.py` - Form fields, submit button, results table

Example:
```python
# Before (placeholder)
USERNAME_INPUT = (By.ID, "username")  # TODO: Update with actual selector

# After (actual)
USERNAME_INPUT = (By.CSS_SELECTOR, "input[name='availity-username']")
```

### Error Artifacts

When errors occur, the bot captures:
- Screenshot: `artifacts/error_{request_id}_{timestamp}.png`
- HTML source: `artifacts/error_{request_id}_{timestamp}.html`

These help diagnose portal changes or unexpected errors.

## Development

### Type Checking

```bash
pip install mypy
mypy .
```

### Linting

```bash
pip install ruff
ruff check .
ruff format .
```

### Adding New Migrations

```bash
# After modifying db/models.py
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

## Architecture Notes

### Async by Default

All database operations use SQLAlchemy async patterns with `asyncpg`. This allows for better scalability and concurrent request processing in the future.

### Retry Strategy

The bot uses Tenacity for retry logic:
- **Transient errors**: Retried up to 2 times with exponential backoff
- **Validation errors**: Not retried (fail immediately)
- **Portal changed errors**: Not retried (manual intervention needed)

### Repository Pattern

Database access is abstracted through `repo_eligibility.py`, providing:
- Transactional guarantees
- Simplified testing
- Clear separation of concerns

## Troubleshooting

### Chrome/ChromeDriver Issues

The project uses Selenium Manager (4.15+) which automatically downloads the correct ChromeDriver. No manual setup needed.

### Database Connection Errors

Verify PostgreSQL is running and the `DATABASE_URL` in `.env` is correct:

```bash
# Test connection (requires psql)
psql postgresql://user:pass@localhost:5432/availity_rpa -c "SELECT 1;"
```

### Portal Selector Changes

If the bot fails with element not found errors:
1. Check `artifacts/` for screenshots showing the actual portal state
2. Update selectors in the relevant page object
3. Consider adding more robust waits or alternative locators

## License

Internal use only.

