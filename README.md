# Availity RPA - Eligibility & Claim Status Workflows

Production-style RPA project for automated eligibility checking and claim status inquiry through the Availity web portal.

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
│   ├── eligibility_models.py # Eligibility Pydantic models
│   └── claim_status_models.py # Claim Status Pydantic models
├── db/                      # Database layer
│   ├── engine.py            # Async engine & session
│   ├── models.py            # SQLAlchemy ORM models
│   ├── repo_eligibility.py  # Eligibility CRUD operations
│   └── repo_claim_status.py # Claim Status CRUD operations
├── pages/                   # Page Objects (Selenium)
│   ├── base_page.py         # Base page utilities
│   ├── login_page.py        # Login page
│   ├── dashboard_page.py    # Dashboard navigation
│   ├── eligibility_page.py  # Eligibility form & results
│   └── claim_status_page.py # Claim Status form & results
├── bots/                    # Bot implementations
│   ├── eligibility_bot.py   # Eligibility workflow bot
│   └── claim_status_bot.py  # Claim Status workflow bot
├── scripts/                 # Executable scripts
│   ├── db_init.py           # Initialize database
│   ├── enqueue_sample.py    # Enqueue test request
│   ├── run_eligibility.py   # Eligibility CLI entry point
│   └── run_claim_status.py  # Claim Status CLI entry point
├── sample/                  # Sample data
│   ├── input_eligibility.json
│   ├── output_eligibility.json
│   ├── input_claim_status.json
│   └── output_claim_status.json
└── artifacts/               # Error screenshots & HTML
    ├── eligibility/         # Eligibility artifacts
    └── claim_status/        # Claim Status artifacts
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

### 5. Run Workflows

#### Eligibility Check

**JSON Mode (File-based):**

```bash
python scripts/run_eligibility.py \
  --input sample/input_eligibility.json \
  --output sample/output_eligibility.json
```

**Database Mode (Queue-based):**

```bash
# Enqueue a sample request
python scripts/enqueue_sample.py

# Process the next pending request
python scripts/run_eligibility.py --db
```

#### Claim Status Inquiry

**JSON Mode (File-based):**

```bash
python scripts/run_claim_status.py \
  --input sample/input_claim_status.json \
  --output sample/output_claim_status.json
```

**Database Mode (Queue-based):**

First, run the migration to add claim status tables:

```bash
alembic upgrade head
```

Then enqueue a query (via SQL or helper script) and process it:

```bash
# Process the next pending query
python scripts/run_claim_status.py --db
```

### Additional Options

```bash
# Run in visible browser mode (not headless)
python scripts/run_eligibility.py --db --no-headless
python scripts/run_claim_status.py --db --no-headless

# JSON mode with visible browser
python scripts/run_eligibility.py \
  --input sample/input_eligibility.json \
  --output sample/output_eligibility.json \
  --no-headless

python scripts/run_claim_status.py \
  --input sample/input_claim_status.json \
  --output sample/output_claim_status.json \
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

### Claim Status Workflow

- **claim_status_queries**: Claim status inquiry requests with status tracking
- **claim_status_results**: Parsed claim status results (status, payment info)
- **claim_status_reason_codes**: Reason codes (CARC, RARC, LOCAL) per result

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
   - `pages/dashboard_page.py` - Navigation to eligibility/claim status sections
   - `pages/eligibility_page.py` - Eligibility form fields, submit button, results table
   - `pages/claim_status_page.py` - Claim status form fields, submit button, results grid

Example:
```python
# Before (placeholder)
USERNAME_INPUT = (By.ID, "username")  # TODO: Update with actual selector

# After (actual)
USERNAME_INPUT = (By.CSS_SELECTOR, "input[name='availity-username']")
```

**Claim Status Selectors:**

The claim status page (`pages/claim_status_page.py`) contains extensive TODO comments for all form fields and result parsing. Key areas to update:
- Payer dropdown selection
- Provider/Patient/Subscriber information fields
- Claim information fields (DOS, claim IDs, amount)
- Results grid/table parsing
- Reason codes extraction

### Error Artifacts

When errors occur, the bots capture:
- Screenshot: `artifacts/{workflow}/error_{request_id}_{timestamp}.png`
- HTML source: `artifacts/{workflow}/error_{request_id}_{timestamp}.html`

Where `{workflow}` is either `eligibility` or `claim_status`.

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

## Claim Status Workflow Details

### Setup

1. **Run Migration:**
   ```bash
   alembic upgrade head
   ```
   This creates the three claim status tables: `claim_status_queries`, `claim_status_results`, and `claim_status_reason_codes`.

2. **Enqueue a Query:**
   
   You can enqueue queries directly via SQL or create a helper script. Example SQL:
   ```sql
   INSERT INTO claim_status_queries (
     payer_id, dos_from, payer_claim_id, claim_amount, status
   ) VALUES (
     1, '2025-10-20', 'PAYER-CLM-123456', 125.00, 'PENDING'
   );
   ```

3. **Process Queries:**
   ```bash
   python scripts/run_claim_status.py --db
   ```

### JSON Mode Example

```json
// sample/input_claim_status.json
{
  "request_id": 201,
  "payer_name": "CIGNA HEALTHCARE",
  "payer_claim_id": "PAYER-CLM-123456",
  "provider_claim_id": null,
  "member_id": null,
  "dos_from": "2025-10-20",
  "dos_to": null,
  "claim_amount": 125.00
}
```

Run:
```bash
python scripts/run_claim_status.py \
  --input sample/input_claim_status.json \
  --output sample/output_claim_status.json
```

### Artifacts Location

Claim status artifacts are saved to: `artifacts/claim_status/`

- Screenshots: `error_{query_id}_{timestamp}.png`
- HTML responses: `response_{query_id}_{timestamp}.html`

### Result Structure

The claim status result includes:
- High-level status (RECEIVED, IN_PROCESS, PAID, DENIED, etc.)
- Status code and date
- Payment information (paid amount, allowed amount, check number, payment date)
- Reason codes (CARC, RARC, LOCAL) with descriptions

## License

Internal use only.

