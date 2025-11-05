"""Initialize database and run migrations."""

import asyncio
import subprocess
import sys

from loguru import logger
from rich.console import Console
from sqlalchemy import text

from config import settings
from db import get_session

console = Console()


async def check_database_connection() -> bool:
    """
    Check if database is reachable.

    Returns:
        True if database is reachable, False otherwise
    """
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def run_alembic_migrations() -> bool:
    """
    Run Alembic migrations to upgrade to head.

    Returns:
        True if migrations successful, False otherwise
    """
    try:
        console.print("\n[bold cyan]Running Alembic migrations...[/bold cyan]")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True,
        )
        console.print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Alembic migration failed: {e.stderr}")
        console.print(f"[bold red]Migration failed:[/bold red]\n{e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("Alembic not found. Is it installed?")
        console.print("[bold red]Alembic not found. Please install: pip install alembic[/bold red]")
        return False


async def main() -> int:
    """
    Main function to initialize database.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    console.print("\n[bold green]Database Initialization[/bold green]\n")

    # Show DATABASE_URL (mask password)
    db_url = settings.DATABASE_URL
    if "@" in db_url:
        masked_url = db_url.split("@")[0].split(":")[0] + ":***@" + db_url.split("@")[1]
    else:
        masked_url = db_url
    console.print(f"[cyan]Database URL:[/cyan] {masked_url}\n")

    # Check database connection
    console.print("[bold cyan]Checking database connection...[/bold cyan]")
    if not await check_database_connection():
        console.print("[bold red]FAILED: Database connection failed[/bold red]")
        console.print("\nPlease check:")
        console.print("  1. PostgreSQL is running")
        console.print("  2. DATABASE_URL in .env is correct")
        console.print("  3. Database exists and credentials are valid")
        return 1

    console.print("[bold green]SUCCESS: Database connection successful[/bold green]\n")

    # Run migrations
    if not run_alembic_migrations():
        return 1

    console.print("\n[bold green]SUCCESS: Database initialization complete![/bold green]\n")
    console.print("You can now:")
    console.print("  • Enqueue sample requests: [cyan]python scripts/enqueue_sample.py[/cyan]")
    console.print("  • Run eligibility checks: [cyan]python scripts/run_eligibility.py --db[/cyan]")
    console.print()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

