"""Main CLI script to run claim status checks in JSON or DB mode."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console

from bots import ClaimStatusBot
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
from db import ClaimStatusQueryStatus, get_session
from db.repo_claim_status import get_next_pending_query, mark_failed, save_claim_status_result
from domain.claim_status_models import ClaimStatusQuery

app = typer.Typer()
console = Console()


def parse_date(date_str: str):
    """Parse date string in ISO format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def run_json_mode(input_path: Path, output_path: Path, headless: bool) -> int:
    """
    Run claim status check from JSON file (single request).

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

    # Build ClaimStatusQuery
    query = ClaimStatusQuery(
        request_id=data["request_id"],
        payer_name=data["payer_name"],
        payer_claim_id=data.get("payer_claim_id"),
        provider_claim_id=data.get("provider_claim_id"),
        member_id=data.get("member_id"),
        patient_last_name=data.get("patient_last_name"),
        patient_first_name=data.get("patient_first_name"),
        patient_dob=parse_date(data["patient_dob"]) if data.get("patient_dob") else None,
        subscriber_last_name=data.get("subscriber_last_name"),
        subscriber_first_name=data.get("subscriber_first_name"),
        subscriber_same_as_patient=data.get("subscriber_same_as_patient", True),
        dos_from=parse_date(data["dos_from"]),
        dos_to=parse_date(data["dos_to"]) if data.get("dos_to") else None,
        claim_amount=data.get("claim_amount"),
    )

    set_request_id(query.request_id)

    # Run bot
    console.print("[bold]Running claim status bot...[/bold]\n")
    bot = ClaimStatusBot(
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

        console.print(f"[bold green]SUCCESS: Claim status check completed![/bold green]")
        console.print(f"[cyan]Result saved to:[/cyan] {output_path}\n")

        # Display summary
        if result.high_level_status:
            console.print(f"[green]Status:[/green] {result.high_level_status}")
        if result.status_code:
            console.print(f"[green]Status Code:[/green] {result.status_code}")
        if result.paid_amount:
            console.print(f"[green]Paid Amount:[/green] ${result.paid_amount:.2f}")
        if result.reason_codes:
            console.print(f"[green]Reason Codes Found:[/green] {len(result.reason_codes)}")
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
    Run claim status check from database (pop next pending query).

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
            console.print("[yellow]No pending claim status queries found[/yellow]\n")
            return 0

        await session.commit()  # Commit status change to IN_PROGRESS

    query_id = db_query.id
    set_request_id(query_id)

    console.print(f"[cyan]Processing query ID:[/cyan] {query_id}")
    console.print(f"[cyan]Payer ID:[/cyan] {db_query.payer_id}")
    console.print(f"[cyan]DOS From:[/cyan] {db_query.dos_from}")
    if db_query.payer_claim_id:
        console.print(f"[cyan]Payer Claim ID:[/cyan] {db_query.payer_claim_id}")
    console.print()

    # Load payer details for domain model
    async with get_session() as session:
        from sqlalchemy import select

        from db.models import Payer

        payer_result = await session.execute(select(Payer).where(Payer.id == db_query.payer_id))
        payer = payer_result.scalar_one()

    # Build domain ClaimStatusQuery
    query = ClaimStatusQuery(
        request_id=query_id,
        payer_name=payer.name,
        payer_claim_id=db_query.payer_claim_id,
        provider_claim_id=db_query.provider_claim_id,
        member_id=db_query.member_id,
        dos_from=db_query.dos_from,
        dos_to=db_query.dos_to,
        claim_amount=float(db_query.claim_amount) if db_query.claim_amount else None,
    )

    # Run bot
    console.print("[bold]Running claim status bot...[/bold]\n")
    bot = ClaimStatusBot(
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
            await save_claim_status_result(session, query_id, result, raw_response)
            await session.commit()

        console.print(f"[bold green]SUCCESS: Claim status check completed![/bold green]")
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
                status=ClaimStatusQueryStatus.FAILED_VALIDATION,
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
                status=ClaimStatusQueryStatus.FAILED_PORTAL,
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
                status=ClaimStatusQueryStatus.FAILED_TECH,
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
                status=ClaimStatusQueryStatus.FAILED_TECH,
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
                status=ClaimStatusQueryStatus.FAILED_TECH,
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
    Run claim status check workflow.

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
        output_path = output if output else Path("sample/output_claim_status.json")
        exit_code = run_json_mode(input, output_path, headless)
    else:
        console.print("[bold red]Error: Must specify either --db or --input[/bold red]\n")
        console.print("Examples:")
        console.print("  JSON mode:  [cyan]python scripts/run_claim_status.py --input sample/input_claim_status.json --output sample/output_claim_status.json[/cyan]")
        console.print("  DB mode:    [cyan]python scripts/run_claim_status.py --db[/cyan]")
        console.print()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    app()

