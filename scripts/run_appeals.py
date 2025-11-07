"""Main CLI script to run appeals searches in JSON or DB mode."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console

from bots import AppealsBot
from config import settings
from core import (
    PortalBusinessError,
    PortalChangedError,
    TransientError,
    ValidationError,
    clear_request_id,
    set_request_id,
    setup_logging,
)
from db import AppealsQueryStatus, get_session
from db.repo_appeals import get_next_pending_query, mark_failed, save_appeals_result
from domain.appeals_models import AppealsQuery

app = typer.Typer()
console = Console()


def run_json_mode(input_path: Path, output_path: Path, headless: bool) -> int:
    """
    Run appeals search from JSON file (single request).

    Args:
        input_path: Input JSON file path
        output_path: Output JSON file path
        headless: Run in headless mode

    Returns:
        Exit code
    """
    console.print(f"\n[bold cyan]JSON Mode[/bold cyan]\n")
    console.print(f"[cyan]Input:[/cyan]  {input_path}")
    console.print(f"[cyan]Output:[/cyan] {output_path}\n")

    # Load input
    if not input_path.exists():
        console.print(f"[bold red]Error: Input file not found: {input_path}[/bold red]")
        return 1

    data = json.loads(input_path.read_text())

    # Build AppealsQuery
    query = AppealsQuery(
        request_id=data["request_id"],
        search_by=data["search_by"],
        search_term=data["search_term"],
    )

    set_request_id(query.request_id)

    # Run bot
    console.print("[bold]Running appeals bot...[/bold]\n")
    bot = AppealsBot(
        base_url=settings.BASE_URL,
        username=settings.USERNAME,
        password=settings.PASSWORD,
        headless=headless,
        artifacts_dir=settings.ARTIFACTS_DIR,
    )

    try:
        result = bot.process_query(query)

        # Write output JSON with parsed results
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.model_dump_json(indent=2))

        console.print(f"[bold green]SUCCESS: Appeals search completed![/bold green]")
        console.print(f"[cyan]Result saved to:[/cyan] {output_path}\n")

        # Display summary
        console.print(f"[green]Appeals Found:[/green] {result.appeals_found}")
        if result.appeals:
            console.print(f"[green]Appeals:[/green] {len(result.appeals)}")
        console.print()

        return 0

    except (ValidationError, PortalChangedError, PortalBusinessError) as e:
        console.print(f"[bold red]FAILED: {type(e).__name__}[/bold red]")
        console.print(f"[red]{e}[/red]\n")
        bot._capture_error_artifacts(query, e)
        return 1

    except TransientError as e:
        console.print(f"[bold red]FAILED after retries: {e}[/bold red]\n")
        bot._capture_error_artifacts(query, e)
        return 1

    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[bold red]UNEXPECTED ERROR: {e}[/bold red]\n")
        bot._capture_error_artifacts(query, e)
        return 1

    finally:
        bot.close()
        clear_request_id()


async def run_db_mode(headless: bool) -> int:
    """
    Run appeals search from database (pop next pending query).

    Args:
        headless: Run in headless mode

    Returns:
        Exit code
    """
    console.print(f"\n[bold cyan]Database Mode[/bold cyan]\n")

    # Get next pending query
    async with get_session() as session:
        db_query = await get_next_pending_query(session)

        if db_query is None:
            console.print("[yellow]No pending appeals queries found[/yellow]\n")
            return 0

        await session.commit()  # Commit status change to IN_PROGRESS

    query_id = db_query.id
    set_request_id(query_id)

    console.print(f"[cyan]Processing query ID:[/cyan] {query_id}")
    console.print(f"[cyan]Search By:[/cyan] {db_query.search_by}")
    console.print(f"[cyan]Search Term:[/cyan] {db_query.search_term}")
    console.print()

    # Build domain AppealsQuery
    query = AppealsQuery(
        request_id=query_id,
        search_by=db_query.search_by,
        search_term=db_query.search_term,
    )

    # Run bot
    console.print("[bold]Running appeals bot...[/bold]\n")
    bot = AppealsBot(
        base_url=settings.BASE_URL,
        username=settings.USERNAME,
        password=settings.PASSWORD,
        headless=headless,
        artifacts_dir=settings.ARTIFACTS_DIR,
    )

    try:
        result = bot.process_query(query)

        # Save result to database
        async with get_session() as session:
            raw_response = {"html_path": result.raw_response_html_path} if result.raw_response_html_path else None
            await save_appeals_result(session, query_id, result, raw_response)
            await session.commit()

        console.print(f"[bold green]SUCCESS: Appeals search completed![/bold green]")
        console.print(f"[cyan]Result saved to database[/cyan]\n")

        return 0

    except ValidationError as e:
        console.print(f"[bold red]FAILED: Validation Error[/bold red]")
        console.print(f"[red]{e}[/red]\n")
        bot._capture_error_artifacts(query, e)

        async with get_session() as session:
            await mark_failed(
                session,
                query_id,
                error_code="VALIDATION_ERROR",
                error_message=str(e),
                status=AppealsQueryStatus.FAILED_VALIDATION,
            )
            await session.commit()

        return 1

    except PortalBusinessError as e:
        console.print(f"[bold yellow]FAILED: Portal Business Error[/bold yellow]")
        console.print(f"[yellow]{e}[/yellow]\n")
        bot._capture_error_artifacts(query, e)

        async with get_session() as session:
            await mark_failed(
                session,
                query_id,
                error_code="PORTAL_BUSINESS_ERROR",
                error_message=str(e),
                status=AppealsQueryStatus.FAILED_PORTAL,
            )
            await session.commit()

        return 1

    except PortalChangedError as e:
        console.print(f"[bold red]FAILED: Portal Changed Error[/bold red]")
        console.print(f"[red]{e}[/red]")
        console.print("[yellow]Manual intervention required - selectors may need updating[/yellow]\n")
        bot._capture_error_artifacts(query, e)

        async with get_session() as session:
            await mark_failed(
                session,
                query_id,
                error_code="PORTAL_CHANGED",
                error_message=str(e),
                status=AppealsQueryStatus.FAILED_TECH,
            )
            await session.commit()

        return 1

    except TransientError as e:
        console.print(f"[bold red]FAILED after retries[/bold red]")
        console.print(f"[red]{e}[/red]\n")
        bot._capture_error_artifacts(query, e)

        async with get_session() as session:
            await mark_failed(
                session,
                query_id,
                error_code="TRANSIENT_ERROR",
                error_message=str(e),
                status=AppealsQueryStatus.FAILED_TECH,
            )
            await session.commit()

        return 1

    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[bold red]UNEXPECTED ERROR: {e}[/bold red]\n")
        bot._capture_error_artifacts(query, e)

        async with get_session() as session:
            await mark_failed(
                session,
                query_id,
                error_code="UNEXPECTED_ERROR",
                error_message=str(e),
                status=AppealsQueryStatus.FAILED_TECH,
            )
            await session.commit()

        return 1

    finally:
        bot.close()
        clear_request_id()


@app.command()
def main(
    input: Optional[Path] = typer.Option(None, "--input", "-i", help="Input JSON file (JSON mode)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output JSON file (JSON mode)"),
    db: bool = typer.Option(False, "--db", help="Run in database mode (process next pending query)"),
    headless: bool = typer.Option(settings.SELENIUM_HEADLESS, "--headless/--no-headless", help="Run browser in headless mode"),
) -> None:
    """
    Run appeals search workflow.

    Modes:
    - JSON mode: --input <file> --output <file>
    - DB mode: --db
    """
    setup_logging(log_level="INFO")

    # Validate mode selection
    if db:
        # Database mode
        exit_code = asyncio.run(run_db_mode(headless))
    elif input:
        # JSON mode
        output_path = output if output else Path("sample/output_appeals.json")
        exit_code = run_json_mode(input, output_path, headless)
    else:
        console.print("[bold red]Error: Must specify either --db or --input[/bold red]\n")
        console.print("Examples:")
        console.print("  JSON mode:  [cyan]python scripts/run_appeals.py --input sample/input_appeals.json --output sample/output_appeals.json[/cyan]")
        console.print("  DB mode:    [cyan]python scripts/run_appeals.py --db[/cyan]")
        console.print()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    app()

