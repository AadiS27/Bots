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
    Run eligibility check from JSON file (single request or array of requests).

    Supports two input formats:
    - Single object: {"request_id": 101, ...}
    - Array of objects: [{"request_id": 101, ...}, {"request_id": 102, ...}]

    Args:
        input_path: Input JSON file path
        output_path: Output JSON file path
        headless: Run in headless mode

    Returns:
        Exit code (0 if all succeeded, 1 if any failed)
    """
    console.print(f"\n[bold cyan]JSON Mode[/bold cyan]\n")
    console.print(f"[cyan]Input:[/cyan]  {input_path}")
    console.print(f"[cyan]Output:[/cyan] {output_path}\n")

    # Load input
    if not input_path.exists():
        console.print(f"[bold red]Error: Input file not found: {input_path}[/bold red]")
        return 1

    data = json.loads(input_path.read_text())

    # Normalize to list: support both single object and array
    if isinstance(data, dict):
        requests_data = [data]
        is_single = True
    elif isinstance(data, list):
        requests_data = data
        is_single = False
    else:
        console.print(f"[bold red]Error: Input JSON must be an object or array of objects[/bold red]")
        return 1

    console.print(f"[cyan]Processing {len(requests_data)} request(s)...[/cyan]\n")

    # Parse all requests
    requests = []
    for idx, req_data in enumerate(requests_data, 1):
        try:
            request = EligibilityRequest(
                request_id=req_data["request_id"],
                payer_name=req_data["payer_name"],
                member_id=req_data["member_id"],
                patient_last_name=req_data["patient_last_name"],
                patient_first_name=req_data.get("patient_first_name"),
                dob=parse_date(req_data["dob"]),
                dos_from=parse_date(req_data["dos_from"]),
                dos_to=parse_date(req_data["dos_to"]) if req_data.get("dos_to") else None,
                service_type_code=req_data.get("service_type_code"),
                provider_npi=req_data.get("provider_npi"),
            )
            requests.append(request)
        except Exception as e:
            console.print(f"[bold red]Error parsing request {idx}: {e}[/bold red]")
            return 1

    # Initialize bot once (reuse for all requests)
    bot = EligibilityBot(
        base_url=settings.BASE_URL,
        username=settings.USERNAME,
        password=settings.PASSWORD,
        headless=headless,
        artifacts_dir=settings.ARTIFACTS_DIR,
    )

    results = []
    failed_count = 0

    try:
        # Process each request
        for idx, request in enumerate(requests, 1):
            set_request_id(request.request_id)

            console.print(f"[bold]Processing request {idx}/{len(requests)} (ID: {request.request_id})...[/bold]")
            console.print(f"[cyan]Member ID:[/cyan] {request.member_id}")
            console.print(f"[cyan]Payer:[/cyan] {request.payer_name}\n")

            try:
                result = bot.process_request(request)
                results.append(result)
                console.print(f"[bold green]SUCCESS: Request {idx} completed![/bold green]\n")

            except (ValidationError, PortalChangedError, PortalBusinessError) as e:
                console.print(f"[bold red]FAILED: Request {idx} - {type(e).__name__}[/bold red]")
                console.print(f"[red]{e}[/red]\n")
                bot._capture_error_artifacts(request, e)
                failed_count += 1
                # Create a failed result entry
                from domain.eligibility_models import EligibilityResult
                failed_result = EligibilityResult(
                    request_id=request.request_id,
                    coverage_status=None,
                    plan_name=None,
                )
                results.append(failed_result)

            except TransientError as e:
                console.print(f"[bold red]FAILED: Request {idx} - Transient error after retries[/bold red]")
                console.print(f"[red]{e}[/red]\n")
                bot._capture_error_artifacts(request, e)
                failed_count += 1
                from domain.eligibility_models import EligibilityResult
                failed_result = EligibilityResult(
                    request_id=request.request_id,
                    coverage_status=None,
                    plan_name=None,
                )
                results.append(failed_result)

            except Exception as e:
                logger.exception(f"Unexpected error processing request {idx}")
                console.print(f"[bold red]UNEXPECTED ERROR: Request {idx} - {e}[/bold red]\n")
                bot._capture_error_artifacts(request, e)
                failed_count += 1
                from domain.eligibility_models import EligibilityResult
                failed_result = EligibilityResult(
                    request_id=request.request_id,
                    coverage_status=None,
                    plan_name=None,
                )
                results.append(failed_result)

            finally:
                clear_request_id()

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if is_single and len(results) == 1:
            # Single request: output as single object
            output_path.write_text(results[0].model_dump_json(indent=2))
        else:
            # Multiple requests: output as array
            output_data = [r.model_dump() for r in results]
            output_path.write_text(json.dumps(output_data, indent=2, default=str))

        # Summary
        success_count = len(results) - failed_count
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"[green]Success:[/green] {success_count}/{len(requests)}")
        if failed_count > 0:
            console.print(f"[red]Failed:[/red] {failed_count}/{len(requests)}")
        console.print(f"[cyan]Results saved to:[/cyan] {output_path}\n")

        return 0 if failed_count == 0 else 1

    finally:
        bot.close()


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
    # Note: provider_npi is not in DB model yet - for now set to None
    # TODO: Add provider_npi column to eligibility_requests table
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
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output JSON file (JSON mode)"),
    db: bool = typer.Option(False, "--db", help="Run in database mode (process next pending request)"),
    headless: bool = typer.Option(settings.SELENIUM_HEADLESS, "--headless/--no-headless", help="Run browser in headless mode"),
) -> None:
    """
    Run eligibility check workflow.

    Modes:
    - JSON mode: --input <file> --output <file>
    - DB mode: --db
    """
    setup_logging(log_level="INFO")

    # Validate mode selection
    if db:
        # Database mode
        exit_code = asyncio.run(run_db_mode(headless))
    elif input and output:
        # JSON mode
        exit_code = run_json_mode(input, output, headless)
    else:
        console.print("[bold red]Error: Must specify either --db or --input/--output[/bold red]\n")
        console.print("Examples:")
        console.print("  JSON mode:  [cyan]python scripts/run_eligibility.py --input sample/input_eligibility.json --output sample/output_eligibility.json[/cyan]")
        console.print("  DB mode:    [cyan]python scripts/run_eligibility.py --db[/cyan]")
        console.print()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    app()

