# Availity Eligibility Bot

Automated eligibility checking bot for Availity portal using Selenium WebDriver and PostgreSQL.

## Features

- ✅ Automated login with 2FA support
- ✅ Form filling with retry logic
- ✅ Database storage of requests and results
- ✅ JSON mode for quick testing
- ✅ Database mode for production batch processing
- ✅ Error handling and screenshot capture
- ✅ Comprehensive logging

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ (or Docker)
- Chrome/Chromium browser
- ChromeDriver (automatically managed by webdriver-manager)

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
cd bots

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example environment file
copy env.example .env

# Edit .env file with your credentials
# Required:
# - USERNAME=your_availity_username
# - PASSWORD=your_availity_password
# - DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/availity_bot
```

**Important for Windows:** If your Windows username differs from your Availity username, set it explicitly:
```powershell
$env:USERNAME="YourAvailityUsername"
```

### 3. Setup Database

#### Option A: Using Docker (Recommended)

```bash
# Start PostgreSQL container
docker run -d \
  --name availity-postgres \
  -e POSTGRES_USER=availity_user \
  -e POSTGRES_PASSWORD=availity_pass \
  -e POSTGRES_DB=availity_bot \
  -p 5432:5432 \
  postgres:14

# Update DATABASE_URL in .env:
# DATABASE_URL=postgresql+asyncpg://availity_user:availity_pass@localhost:5432/availity_bot
```

#### Option B: Local PostgreSQL

1. Install PostgreSQL
2. Create database: `CREATE DATABASE availity_bot;`
3. Update `DATABASE_URL` in `.env`

### 4. Initialize Database

```bash
# Set PYTHONPATH (Windows)
set PYTHONPATH=E:\QuickIntell11\bots

# Initialize database and run migrations
python scripts/db_init.py
```

### 5. Run the Bot

#### JSON Mode (Testing)

**Single Request:**
```bash
# Run with single request JSON file
python scripts/run_eligibility.py \
  --input sample/input_eligibility.json \
  --output sample/output_test.json \
  --no-headless
```

**Multiple Requests:**
```bash
# Run with multiple requests in JSON array
python scripts/run_eligibility.py \
  --input sample/input_eligibility_multiple.json \
  --output sample/output_multiple.json \
  --no-headless
```

The bot will:
- Login once (reuse session for all requests)
- Process each request sequentially
- Show progress for each request
- Save all results to the output file

#### Database Mode (Production)

```bash
# Step 1: Enqueue requests
python scripts/enqueue_sample.py

# Step 2: Process requests (run multiple times for batch processing)
python scripts/run_eligibility.py --db --no-headless

# Step 3: View results
python scripts/show_db_data.py
```

## Detailed Usage

### Enqueuing Requests

#### From JSON File

```bash
python scripts/enqueue_sample.py
```

This reads `sample/input_eligibility.json` and enqueues it to the database.

#### Multiple Requests

```bash
python scripts/test_multiple_requests.py
```

This enqueues 3 test requests with different member IDs.

### Processing Requests

The bot processes requests in FIFO order (oldest first):

```bash
# Process one request at a time
python scripts/run_eligibility.py --db --no-headless

# Run multiple times to process all pending requests
```

**Note:** The bot will:
- Automatically handle 2FA (gives you 2 minutes to enter code manually)
- Navigate to eligibility page (currently requires manual navigation)
- Fill form and submit
- Store results in database

### Viewing Results

```bash
# View all database data
python scripts/show_db_data.py
```

This shows:
- Request statistics by status
- All eligibility requests
- Eligibility results
- Payers and patients

### Checking Database Status

```sql
-- Connect to PostgreSQL
psql -U availity_user -d availity_bot

-- View pending requests
SELECT id, member_id, status, created_at 
FROM eligibility_requests 
WHERE status = 'PENDING'
ORDER BY created_at ASC;

-- View results
SELECT er.id, er.member_id, er.status, res.coverage_status, res.plan_name
FROM eligibility_requests er
LEFT JOIN eligibility_results res ON res.eligibility_request_id = er.id
ORDER BY er.id DESC;
```

## Input Format

### JSON Input - Single Request

**File:** `sample/input_eligibility.json`

```json
{
  "request_id": 101,
  "payer_name": "CIGNA HEALTHCARE",
  "member_id": "AB123456789",
  "patient_last_name": "DOE",
  "patient_first_name": "JOHN",
  "dob": "1987-06-15",
  "dos_from": "2025-11-05",
  "dos_to": null,
  "service_type_code": "30",
  "provider_npi": "1234567890"
}
```

### JSON Input - Multiple Requests

**File:** `sample/input_eligibility_multiple.json`

```json
[
  {
    "request_id": 101,
    "payer_name": "CIGNA HEALTHCARE",
    "member_id": "AB123456789",
    "patient_last_name": "DOE",
    "patient_first_name": "JOHN",
    "dob": "1987-06-15",
    "dos_from": "2025-11-05",
    "dos_to": null,
    "service_type_code": "30",
    "provider_npi": "1234567890"
  },
  {
    "request_id": 102,
    "payer_name": "AETNA",
    "member_id": "CD987654321",
    "patient_last_name": "SMITH",
    "patient_first_name": "JANE",
    "dob": "1990-03-20",
    "dos_from": "2025-11-05",
    "dos_to": null,
    "service_type_code": "30",
    "provider_npi": "1234567890"
  }
]
```

**Note:** The bot supports both formats:
- **Single object**: Process one request
- **Array of objects**: Process multiple requests sequentially (reuses login session)

## Workflow

1. **Enqueue**: Add requests to database with `PENDING` status
2. **Process**: Bot picks up oldest `PENDING` request
3. **Status Updates**:
   - `PENDING` → `IN_PROGRESS` (when bot starts processing)
   - `IN_PROGRESS` → `SUCCESS` (if successful)
   - `IN_PROGRESS` → `FAILED_*` (if failed)
4. **Results**: Stored in `eligibility_results` table

## Status Types

- `PENDING`: Request enqueued, waiting to be processed
- `IN_PROGRESS`: Currently being processed by bot
- `SUCCESS`: Successfully completed, results stored
- `FAILED_PORTAL`: Portal returned business error
- `FAILED_TECH`: Technical error (timeout, element not found, etc.)
- `FAILED_VALIDATION`: Invalid input data

## Project Structure

```
bots/
├── alembic/              # Database migrations
├── artifacts/            # Error screenshots and HTML
├── bots/                 # Bot logic
│   └── eligibility_bot.py
├── config/               # Configuration
│   └── settings.py
├── core/                 # Core utilities
│   ├── driver_factory.py
│   ├── errors.py
│   └── logging.py
├── db/                   # Database
│   ├── models.py         # SQLAlchemy models
│   ├── engine.py         # Database engine
│   └── repo_eligibility.py  # Repository pattern
├── domain/               # Domain models (Pydantic)
│   └── eligibility_models.py
├── pages/                # Page Object Model
│   ├── base_page.py
│   ├── login_page.py
│   ├── dashboard_page.py
│   └── eligibility_page.py
├── scripts/              # CLI scripts
│   ├── db_init.py
│   ├── enqueue_sample.py
│   ├── run_eligibility.py
│   ├── show_db_data.py
│   └── test_multiple_requests.py
└── sample/               # Sample files
    ├── input_eligibility.json
    └── output_eligibility.json
```

## Troubleshooting

### Windows Username Issue

If the bot uses the wrong username (Windows username instead of Availity username):

```powershell
# Set it explicitly before running
$env:USERNAME="YourAvailityUsername"
python scripts/run_eligibility.py --db --no-headless
```

### 2FA (Two-Factor Authentication)

The bot gives you 2 minutes to manually enter the 2FA code. Watch the browser window and enter the code when prompted.

### Manual Navigation

Currently, the bot requires you to manually navigate to the eligibility page after login. The bot will wait 30 seconds for you to navigate.

### Form Not Loading

If the eligibility form doesn't load:
- Check if you're in the correct iframe
- Increase wait times in `pages/eligibility_page.py`
- Check error screenshots in `artifacts/` directory

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker ps  # If using Docker

# Test connection
psql -U availity_user -d availity_bot -c "SELECT 1;"
```

## Configuration

### Environment Variables (.env)

```env
# Required
USERNAME=your_availity_username
PASSWORD=your_availity_password
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/availity_bot

# Optional
BASE_URL=https://apps.availity.com
SELENIUM_HEADLESS=false
ARTIFACTS_DIR=artifacts
LOG_LEVEL=INFO
```

## Development

### Running Tests

```bash
# Test login only
python test_login_only.py

# Test navigation
python test_navigation.py
```

### Creating Migrations

```bash
# After modifying models.py
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Adding New Selectors

1. Inspect the portal page
2. Update selectors in `pages/eligibility_page.py`
3. Test with `--no-headless` flag
4. Check error screenshots if it fails

## Best Practices

1. **Always test with `--no-headless` first** to see what's happening
2. **Check error screenshots** in `artifacts/` directory when something fails
3. **Use JSON mode** for quick testing
4. **Use DB mode** for production batch processing
5. **Monitor logs** for detailed execution flow

## Support

For issues or questions:
- Check error screenshots in `artifacts/` directory
- Review logs for detailed error messages
- Check database status with `show_db_data.py`

## License

[Your License Here]
