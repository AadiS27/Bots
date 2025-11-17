"""Main CLI script to run claims submission in JSON or DB mode."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console

from bots import ClaimsBot
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
from domain.claims_models import ClaimsQuery, ServiceLine

app = typer.Typer()
console = Console()


def run_json_mode(input_path: Path, output_path: Path, headless: bool) -> int:
    """
    Run claims submission from JSON file (single request).

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

    # Parse date if provided
    patient_birth_date = None
    if data.get("patient_birth_date"):
        patient_birth_date = datetime.strptime(data["patient_birth_date"], "%Y-%m-%d").date()

    # Parse service lines if provided
    service_lines = []
    if data.get("service_lines"):
        for sl_data in data["service_lines"]:
            sl_from_date = None
            if sl_data.get("from_date"):
                sl_from_date = datetime.strptime(sl_data["from_date"], "%Y-%m-%d").date()
            service_line = ServiceLine(
                from_date=sl_from_date,
                place_of_service_code=sl_data.get("place_of_service_code"),
                procedure_code=sl_data.get("procedure_code"),
                diagnosis_code_pointer1=sl_data.get("diagnosis_code_pointer1"),
                amount=sl_data.get("amount"),
                quantity=sl_data.get("quantity"),
                quantity_type_code=sl_data.get("quantity_type_code", "UN - Unit"),
            )
            service_lines.append(service_line)

    # Build ClaimsQuery
    query = ClaimsQuery(
        request_id=data["request_id"],
        transaction_type=data["transaction_type"],
        payer=data.get("payer"),
        responsibility_sequence=data.get("responsibility_sequence", "Primary"),
        patient_last_name=data.get("patient_last_name"),
        patient_first_name=data.get("patient_first_name"),
        patient_birth_date=patient_birth_date,
        patient_gender_code=data.get("patient_gender_code"),
        patient_subscriber_relationship_code=data.get("patient_subscriber_relationship_code", "Self"),
        patient_address_line1=data.get("patient_address_line1"),
        patient_country_code=data.get("patient_country_code", "United States"),
        patient_city=data.get("patient_city"),
        patient_state_code=data.get("patient_state_code"),
        patient_zip_code=data.get("patient_zip_code"),
        subscriber_member_id=data.get("subscriber_member_id"),
        subscriber_group_number=data.get("subscriber_group_number"),
        patient_paid_amount=data.get("patient_paid_amount"),
        benefits_assignment_certification=data.get("benefits_assignment_certification"),
        claim_control_number=data.get("claim_control_number"),
        place_of_service_code=data.get("place_of_service_code"),
        frequency_type_code=data.get("frequency_type_code"),
        provider_accept_assignment_code=data.get("provider_accept_assignment_code"),
        information_release_code=data.get("information_release_code"),
        provider_signature_on_file=data.get("provider_signature_on_file"),
        payer_claim_filing_indicator_code=data.get("payer_claim_filing_indicator_code", "CI - Commercial Insurance Co."),
        medical_record_number=data.get("medical_record_number"),
        billing_provider_last_name=data.get("billing_provider_last_name"),
        billing_provider_first_name=data.get("billing_provider_first_name"),
        billing_provider_npi=data.get("billing_provider_npi"),
        billing_provider_tax_id_ein=data.get("billing_provider_tax_id_ein"),
        billing_provider_tax_id_ssn=data.get("billing_provider_tax_id_ssn"),
        billing_provider_specialty_code=data.get("billing_provider_specialty_code"),
        billing_provider_address_line1=data.get("billing_provider_address_line1"),
        billing_provider_country_code=data.get("billing_provider_country_code", "United States"),
        billing_provider_city=data.get("billing_provider_city"),
        billing_provider_state_code=data.get("billing_provider_state_code"),
        billing_provider_zip_code=data.get("billing_provider_zip_code"),
        diagnosis_code=data.get("diagnosis_code"),
        service_lines=service_lines,
    )

    set_request_id(query.request_id)

    # Run bot
    console.print("[bold]Running claims submission bot...[/bold]\n")
    bot = ClaimsBot(
        base_url=settings.BASE_URL,
        username=settings.USERNAME,
        password=settings.PASSWORD,
        headless=headless,
        artifacts_dir=settings.ARTIFACTS_DIR,
    )

    result = None
    try:
        result = bot.process_query(query)

        # Write output JSON with parsed results
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.model_dump_json(indent=2))

        console.print(f"[bold green]SUCCESS: Claims submission completed![/bold green]")
        console.print(f"[cyan]Result saved to:[/cyan] {output_path}\n")

        # Display summary
        if result.submission_status:
            console.print(f"[green]Status:[/green] {result.submission_status}")
        if result.claim_id:
            console.print(f"[green]Claim ID:[/green] {result.claim_id}")
        if result.transaction_id:
            console.print(f"[green]Transaction ID:[/green] {result.transaction_id}")
        if result.error_message:
            console.print(f"[yellow]Error:[/yellow] {result.error_message}")
        console.print()

        return 0

    except (ValidationError, PortalChangedError, PortalBusinessError) as e:
        console.print(f"[bold red]FAILED: {type(e).__name__}[/bold red]")
        console.print(f"[red]{e}[/red]\n")
        bot._capture_error_artifacts(query, e)
        
        # Write error result to output file
        from domain.claims_models import ClaimsResult
        error_result = ClaimsResult(
            request_id=query.request_id,
            submission_status="FAILED",
            claim_submitted=None,
            claim_id=None,
            transaction_id=None,
            patient_account_number=None,
            submission_type=None,
            submission_date=None,
            dates_of_service=None,
            patient_name=None,
            subscriber_id=None,
            billing_provider_name=None,
            billing_provider_npi=None,
            billing_provider_tax_id=None,
            total_charges=None,
            error_message=str(e),
            raw_response_html_path=None,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(error_result.model_dump_json(indent=2))
        console.print(f"[cyan]Error result saved to:[/cyan] {output_path}\n")
        
        return 1

    except TransientError as e:
        console.print(f"[bold red]FAILED after retries: {e}[/bold red]\n")
        bot._capture_error_artifacts(query, e)
        
        # Write error result to output file
        from domain.claims_models import ClaimsResult
        error_result = ClaimsResult(
            request_id=query.request_id,
            submission_status="FAILED",
            claim_id=None,
            transaction_id=None,
            patient_account_number=None,
            submission_type=None,
            submission_date=None,
            dates_of_service=None,
            patient_name=None,
            subscriber_id=None,
            billing_provider_name=None,
            billing_provider_npi=None,
            billing_provider_tax_id=None,
            total_charges=None,
            error_message=f"Transient error: {str(e)}",
            raw_response_html_path=None,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(error_result.model_dump_json(indent=2))
        console.print(f"[cyan]Error result saved to:[/cyan] {output_path}\n")
        
        return 1

    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[bold red]UNEXPECTED ERROR: {e}[/bold red]\n")
        bot._capture_error_artifacts(query, e)
        
        # Write error result to output file
        from domain.claims_models import ClaimsResult
        error_result = ClaimsResult(
            request_id=query.request_id,
            submission_status="FAILED",
            claim_id=None,
            transaction_id=None,
            patient_account_number=None,
            submission_type=None,
            submission_date=None,
            dates_of_service=None,
            patient_name=None,
            subscriber_id=None,
            billing_provider_name=None,
            billing_provider_npi=None,
            billing_provider_tax_id=None,
            total_charges=None,
            error_message=f"Unexpected error: {str(e)}",
            raw_response_html_path=None,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(error_result.model_dump_json(indent=2))
        console.print(f"[cyan]Error result saved to:[/cyan] {output_path}\n")
        
        return 1

    finally:
        bot.close()
        clear_request_id()


@app.command()
def main(
    input: Optional[Path] = typer.Option(None, "--input", "-i", help="Input JSON file (JSON mode)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output JSON file (JSON mode)"),
    headless: bool = typer.Option(settings.SELENIUM_HEADLESS, "--headless/--no-headless", help="Run browser in headless mode"),
) -> None:
    """
    Run claims submission workflow.

    Modes:
    - JSON mode: --input <file> --output <file>
    """
    setup_logging(log_level="INFO")

    # Validate mode selection
    if input:
        # JSON mode
        output_path = output if output else Path("sample/output_claims.json")
        exit_code = run_json_mode(input, output_path, headless)
    else:
        console.print("[bold red]Error: Must specify --input[/bold red]\n")
        console.print("Examples:")
        console.print("  JSON mode:  [cyan]python scripts/run_claims.py --input sample/input_claims.json --output sample/output_claims.json[/cyan]")
        console.print()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    app()

