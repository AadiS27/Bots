"""Main CLI script to run eligibility checks in JSON or DB mode."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console

from bots import EligibilityBot
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
from db import EligibilityRequestStatus, get_session
from db.repo_eligibility import get_next_pending_request, mark_failed, save_result
from domain import EligibilityRequest

app = typer.Typer()
console = Console()


def parse_date(date_str: str):
    """Parse date string in ISO format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def run_json_mode(input_path: Path, output_path: Path, headless: bool) -> int:
    """
    Run eligibility check from JSON file (single request).

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

    # Build EligibilityRequest
    request = EligibilityRequest(
        request_id=data["request_id"],
        payer_name=data["payer_name"],
        member_id=data["member_id"],
        patient_last_name=data["patient_last_name"],
        patient_first_name=data.get("patient_first_name"),
        dob=parse_date(data["dob"]),
        dos_from=parse_date(data["dos_from"]),
        dos_to=parse_date(data["dos_to"]) if data.get("dos_to") else None,
        service_type_code=data.get("service_type_code"),
        provider_name=data.get("provider_name"),
        provider_npi=data.get("provider_npi"),
    )

    set_request_id(request.request_id)

    # Run bot
    console.print("[bold]Running eligibility bot...[/bold]\n")
    bot = EligibilityBot(
        base_url=settings.BASE_URL,
        username=settings.USERNAME,
        password=settings.PASSWORD,
        headless=headless,
        artifacts_dir=settings.ARTIFACTS_DIR,
    )

    try:
        result = bot.process_request(request)

        # Write output JSON with parsed results
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.model_dump_json(indent=2))

        console.print(f"[bold green]SUCCESS: Eligibility check completed![/bold green]")
        console.print(f"[cyan]Result saved to:[/cyan] {output_path}\n")
        
        # Display summary
        if result.coverage_status:
            console.print(f"[green]Coverage Status:[/green] {result.coverage_status}")
        if result.plan_name:
            console.print(f"[green]Plan Name:[/green] {result.plan_name}")
        if result.benefit_lines:
            console.print(f"[green]Benefit Lines Found:[/green] {len(result.benefit_lines)}")
        console.print()

        return 0

    except (ValidationError, PortalChangedError, PortalBusinessError) as e:
        console.print(f"[bold red]FAILED: {type(e).__name__}[/bold red]")
        console.print(f"[red]{e}[/red]\n")
        bot._capture_error_artifacts(request, e)
        return 1

    except TransientError as e:
        console.print(f"[bold red]FAILED after retries: {e}[/bold red]\n")
        bot._capture_error_artifacts(request, e)
        return 1

    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[bold red]UNEXPECTED ERROR: {e}[/bold red]\n")
        bot._capture_error_artifacts(request, e)
        return 1

    finally:
        bot.close()
        clear_request_id()


async def run_db_mode(headless: bool) -> int:
    """
    Run eligibility check from database (pop next pending request).

    Args:
        headless: Run in headless mode

    Returns:
        Exit code
    """
    console.print(f"\n[bold cyan]Database Mode[/bold cyan]\n")

    # Get next pending request
    async with get_session() as session:
        db_request = await get_next_pending_request(session)

        if db_request is None:
            console.print("[yellow]No pending eligibility requests found[/yellow]\n")
            return 0

        await session.commit()  # Commit status change to IN_PROGRESS

    request_id = db_request.id
    set_request_id(request_id)

    console.print(f"[cyan]Processing request ID:[/cyan] {request_id}")
    console.print(f"[cyan]Payer ID:[/cyan] {db_request.payer_id}")
    console.print(f"[cyan]Member ID:[/cyan] {db_request.member_id}")
    console.print(f"[cyan]DOS:[/cyan] {db_request.dos_from}\n")

    # Load payer and patient details for domain model
    async with get_session() as session:
        # Fetch payer name
        from sqlalchemy import select

        from db.models import Payer, Patient

        payer_result = await session.execute(select(Payer).where(Payer.id == db_request.payer_id))
        payer = payer_result.scalar_one()

        patient = None
        if db_request.patient_id:
            patient_result = await session.execute(select(Patient).where(Patient.id == db_request.patient_id))
            patient = patient_result.scalar_one_or_none()

    # Build domain EligibilityRequest
    # Note: provider_name and provider_npi are not in DB model yet - for now set to None
    # TODO: Add provider_name and provider_npi columns to eligibility_requests table
    request = EligibilityRequest(
        request_id=request_id,
        payer_name=payer.name,
        member_id=db_request.member_id,
        patient_last_name=patient.last_name if patient else "UNKNOWN",
        patient_first_name=patient.first_name if patient else None,
        dob=patient.date_of_birth if patient else datetime(1970, 1, 1).date(),
        dos_from=db_request.dos_from,
        dos_to=db_request.dos_to,
        service_type_code=db_request.service_type_code,
        provider_name=None,  # TODO: Read from DB once provider_name column is added
        provider_npi=None,  # TODO: Read from DB once provider_npi column is added
    )

    # Run bot
    console.print("[bold]Running eligibility bot...[/bold]\n")
    bot = EligibilityBot(
        base_url=settings.BASE_URL,
        username=settings.USERNAME,
        password=settings.PASSWORD,
        headless=headless,
        artifacts_dir=settings.ARTIFACTS_DIR,
    )

    try:
        result = bot.process_request(request)

        # Save result to database
        async with get_session() as session:
            await save_result(session, request_id, result)
            await session.commit()

        console.print(f"[bold green]SUCCESS: Eligibility check completed![/bold green]")
        console.print(f"[cyan]Result saved to database[/cyan]\n")

        return 0

    except ValidationError as e:
        console.print(f"[bold red]FAILED: Validation Error[/bold red]")
        console.print(f"[red]{e}[/red]\n")
        bot._capture_error_artifacts(request, e)

        async with get_session() as session:
            await mark_failed(
                session,
                request_id,
                error_code="VALIDATION_ERROR",
                error_message=str(e),
                status=EligibilityRequestStatus.FAILED_VALIDATION,
            )
            await session.commit()

        return 1

    except PortalBusinessError as e:
        console.print(f"[bold yellow]FAILED: Portal Business Error[/bold yellow]")
        console.print(f"[yellow]{e}[/yellow]\n")
        bot._capture_error_artifacts(request, e)

        async with get_session() as session:
            await mark_failed(
                session,
                request_id,
                error_code="PORTAL_BUSINESS_ERROR",
                error_message=str(e),
                status=EligibilityRequestStatus.FAILED_PORTAL,
            )
            await session.commit()

        return 1

    except PortalChangedError as e:
        console.print(f"[bold red]FAILED: Portal Changed Error[/bold red]")
        console.print(f"[red]{e}[/red]")
        console.print("[yellow]Manual intervention required - selectors may need updating[/yellow]\n")
        bot._capture_error_artifacts(request, e)

        async with get_session() as session:
            await mark_failed(
                session,
                request_id,
                error_code="PORTAL_CHANGED",
                error_message=str(e),
                status=EligibilityRequestStatus.FAILED_TECH,
            )
            await session.commit()

        return 1

    except TransientError as e:
        console.print(f"[bold red]FAILED after retries[/bold red]")
        console.print(f"[red]{e}[/red]\n")
        bot._capture_error_artifacts(request, e)

        async with get_session() as session:
            await mark_failed(
                session,
                request_id,
                error_code="TRANSIENT_ERROR",
                error_message=str(e),
                status=EligibilityRequestStatus.FAILED_TECH,
            )
            await session.commit()

        return 1

    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[bold red]UNEXPECTED ERROR: {e}[/bold red]\n")
        bot._capture_error_artifacts(request, e)

        async with get_session() as session:
            await mark_failed(
                session,
                request_id,
                error_code="UNEXPECTED_ERROR",
                error_message=str(e),
                status=EligibilityRequestStatus.FAILED_TECH,
            )
            await session.commit()

        return 1

    finally:
        bot.close()
        clear_request_id()


@app.command()
def main(
    input: Optional[Path] = typer.Option(None, "--input", "-i", help="Input JSON file (JSON mode)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output JSON file (JSON mode - currently not used, results not saved)"),
    db: bool = typer.Option(False, "--db", help="Run in database mode (process next pending request)"),
    headless: bool = typer.Option(settings.SELENIUM_HEADLESS, "--headless/--no-headless", help="Run browser in headless mode"),
) -> None:
    """
    Run eligibility check workflow.

    Modes:
    - JSON mode: --input <file> [--output <file>] (output optional, not currently used)
    - DB mode: --db
    """
    setup_logging(log_level="INFO")

    # Validate mode selection
    if db:
        # Database mode
        exit_code = asyncio.run(run_db_mode(headless))
    elif input:
        # JSON mode (output is optional and not used)
        output_path = output if output else Path("sample/output_eligibility.json")  # Default if not provided
        exit_code = run_json_mode(input, output_path, headless)
    else:
        console.print("[bold red]Error: Must specify either --db or --input[/bold red]\n")
        console.print("Examples:")
        console.print("  JSON mode:  [cyan]python scripts/run_eligibility.py --input sample/input_eligibility.json[/cyan]")
        console.print("  DB mode:    [cyan]python scripts/run_eligibility.py --db[/cyan]")
        console.print()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    app()

