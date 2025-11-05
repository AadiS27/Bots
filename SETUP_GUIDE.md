# Setup Guide - Availity RPA Project

This guide provides step-by-step instructions to get the Availity RPA project running.

## Prerequisites

- **Python 3.11+** installed
- **PostgreSQL 16** running (or Docker to run it)
- **Git** (optional, for version control)
- **Chrome browser** installed (ChromeDriver auto-managed by Selenium Manager)

## Installation Steps

### 1. Clone or Download Project

If using Git:
```bash
git clone <repository-url>
cd availity_rpa
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

Activate it:
- **macOS/Linux**: `source .venv/bin/activate`
- **Windows PowerShell**: `.venv\Scripts\Activate.ps1`
- **Windows CMD**: `.venv\Scripts\activate.bat`

### 3. Install Dependencies

Using requirements.txt:
```bash
pip install -r requirements.txt
```

Or using pyproject.toml:
```bash
pip install -e .
```

### 4. Configure Environment Variables

Copy the template:
```bash
cp env.example .env
```

Edit `.env` with your actual values:
```
BASE_URL=https://apps.availity.com
USERNAME=your_actual_username
PASSWORD=your_actual_password
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/availity_rpa
SELENIUM_HEADLESS=true
PAGELOAD_TIMEOUT=60
EXPLICIT_TIMEOUT=20
ARTIFACTS_DIR=artifacts
```

**Important**: Never commit your `.env` file (it's in `.gitignore`)

### 5. Start PostgreSQL

#### Option A: Using Docker (Recommended)

```bash
docker run --name availity-pg \
  -e POSTGRES_PASSWORD=pass \
  -e POSTGRES_USER=user \
  -e POSTGRES_DB=availity_rpa \
  -p 5432:5432 \
  -d postgres:16
```

#### Option B: Local PostgreSQL

1. Install PostgreSQL 16
2. Create database: `createdb availity_rpa`
3. Update `DATABASE_URL` in `.env` with your credentials

### 6. Initialize Database

Run the database initialization script:

```bash
python scripts/db_init.py
```

This will:
- Test database connection
- Enable pgcrypto extension
- Run Alembic migrations to create all tables

Expected output:
```
✓ Database connection successful
✓ Database initialization complete!
```

### 7. Verify Installation

Check that tables were created:

```bash
# Using psql
psql postgresql://user:pass@localhost:5432/availity_rpa -c "\dt"
```

You should see tables:
- payers
- patients
- patient_payer_enrollments
- eligibility_requests
- eligibility_results
- eligibility_benefit_lines

## Testing the Setup

### Test 1: Enqueue Sample Request

```bash
python scripts/enqueue_sample.py
```

Expected output:
```
✓ Enqueued request ID: 1
```

### Test 2: Run in JSON Mode (Placeholder Selectors)

```bash
python scripts/run_eligibility.py \
  --input sample/input_eligibility.json \
  --output sample/output_eligibility.json \
  --no-headless
```

**Note**: This will fail with placeholder selectors, but you should see:
- Chrome browser opens
- Login page loads
- Error artifacts saved to `artifacts/`

This confirms the framework is working!

### Test 3: Run in DB Mode

```bash
python scripts/run_eligibility.py --db --no-headless
```

Same as above - framework works, but needs real selectors.

## Next Steps: Update Selectors

The project uses **placeholder selectors** that need to be replaced with actual Availity portal selectors.

### Files to Update

1. **`pages/login_page.py`**
   - `USERNAME_INPUT`
   - `PASSWORD_INPUT`
   - `LOGIN_BUTTON`
   - `DASHBOARD_MARKER`

2. **`pages/dashboard_page.py`**
   - `ELIGIBILITY_MENU`
   - `ELIGIBILITY_LINK`
   - `ELIGIBILITY_PAGE_MARKER`

3. **`pages/eligibility_page.py`**
   - All form field selectors
   - All result field selectors
   - Benefits table selectors

### How to Find Real Selectors

1. Open Availity portal in Chrome
2. Log in manually
3. Navigate to eligibility section
4. Right-click elements → Inspect
5. Find stable selectors (prefer `id`, `data-testid`, or unique classes)
6. Update the `TODO` lines in page objects

Example:
```python
# Before (placeholder)
USERNAME_INPUT = (By.ID, "username")  # TODO: Update

# After (actual selector found via inspect)
USERNAME_INPUT = (By.CSS_SELECTOR, "input[name='availity-username']")
```

## Troubleshooting

### Database Connection Failed

**Symptoms**: `Database connection failed` error

**Solutions**:
- Verify PostgreSQL is running: `docker ps` or `pg_ctl status`
- Check DATABASE_URL in `.env` matches your setup
- Test connection: `psql <DATABASE_URL> -c "SELECT 1"`

### Alembic Migration Failed

**Symptoms**: Alembic errors during `db_init.py`

**Solutions**:
- Ensure database exists: `createdb availity_rpa`
- Check alembic.ini has correct path
- Manually run: `alembic upgrade head` for more details

### ChromeDriver Issues

**Symptoms**: WebDriver errors

**Solutions**:
- Update Chrome to latest version
- Update selenium: `pip install --upgrade selenium`
- Selenium Manager (4.15+) auto-downloads drivers
- Check Chrome is installed and in PATH

### Import Errors

**Symptoms**: `ModuleNotFoundError`

**Solutions**:
- Activate virtual environment
- Reinstall dependencies: `pip install -r requirements.txt`
- Verify Python 3.11+: `python --version`

## Project Structure Reference

```
availity_rpa/
├── config/          # Settings (BASE_URL, credentials, timeouts)
├── core/            # Driver factory, logging, custom errors
├── domain/          # Pydantic models (business logic)
├── db/              # SQLAlchemy models, engine, repository
├── pages/           # Page Objects (login, dashboard, eligibility)
├── bots/            # Bot orchestration with retry logic
├── scripts/         # CLI entry points
├── sample/          # Sample JSON input/output
├── artifacts/       # Error screenshots and HTML (auto-generated)
└── alembic/         # Database migrations
```

## Support

For issues:
1. Check `artifacts/` for error screenshots
2. Check logs in console output
3. Review TODO comments in page objects
4. Verify environment variables in `.env`

## Security Notes

- Never commit `.env` file
- Never commit credentials
- Keep `artifacts/` out of version control (in `.gitignore`)
- Use environment-specific `.env` files for different environments

