"""Test script to process multiple eligibility requests from JSON file."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

from bots.eligibility_bot import EligibilityBot
from config import settings
from domain import EligibilityRequest, EligibilityResult

console = Console()


def load_requests_from_json(filepath: str) -> List[dict]:
    """
    Load eligibility requests from JSON file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        List of request dictionaries
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {filepath}")
    
    with open(path, 'r') as f:
        data = json.load(f)
    
    # Handle both single object and array
    if isinstance(data, dict):
        return [data]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("JSON must contain an object or array of objects")


def create_eligibility_request(data: dict) -> EligibilityRequest:
    """
    Create EligibilityRequest from dictionary.
    
    Args:
        data: Request data dictionary
        
    Returns:
        EligibilityRequest object
    """
    return EligibilityRequest(
        request_id=data.get("request_id"),
        payer_name=data["payer_name"],
        member_id=data["member_id"],
        patient_last_name=data["patient_last_name"],
        patient_first_name=data["patient_first_name"],
        dob=data["dob"],
        dos_from=data.get("dos_from"),
        dos_to=data.get("dos_to"),
        service_type_code=data.get("service_type_code"),
        provider_npi=data.get("provider_npi"),
    )


def save_results_to_json(results: List[EligibilityResult], output_file: str) -> None:
    """
    Save results to JSON file.
    
    Args:
        results: List of EligibilityResult objects
        output_file: Output file path
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert results to dictionaries
    results_data = [result.model_dump(mode='json') for result in results]
    
    with open(output_path, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    console.print(f"[green]✓ Results saved to: {output_path}[/green]")


def display_results_table(results: List[EligibilityResult], errors: List[dict]) -> None:
    """
    Display results in a formatted table.
    
    Args:
        results: List of successful results
        errors: List of error dictionaries
    """
    # Success table
    if results:
        console.print("\n[bold green]✓ Successful Requests[/bold green]")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Request ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Plan Name", style="yellow")
        table.add_column("Plan Type", style="magenta")
        table.add_column("Coverage Dates", style="blue")
        table.add_column("Benefits", style="white")
        
        for result in results:
            coverage_dates = f"{result.coverage_start_date or 'N/A'} to {result.coverage_end_date or 'N/A'}"
            benefit_count = len(result.benefit_lines) if result.benefit_lines else 0
            
            table.add_row(
                str(result.request_id),
                result.coverage_status or "Unknown",
                result.plan_name or "N/A",
                result.plan_type or "N/A",
                coverage_dates,
                str(benefit_count)
            )
        
        console.print(table)
    
    # Error table
    if errors:
        console.print("\n[bold red]✗ Failed Requests[/bold red]")
        error_table = Table(show_header=True, header_style="bold red")
        error_table.add_column("Request ID", style="red")
        error_table.add_column("Error Type", style="yellow")
        error_table.add_column("Error Message", style="white")
        
        for error in errors:
            error_table.add_row(
                str(error["request_id"]),
                error["error_type"],
                error["error_message"][:80] + "..." if len(error["error_message"]) > 80 else error["error_message"]
            )
        
        console.print(error_table)


def main():
    """Main function to process multiple requests from JSON."""
    console.print("\n[bold cyan]╔═══════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║  Multiple Eligibility Requests Test      ║[/bold cyan]")
    console.print("[bold cyan]╚═══════════════════════════════════════════╝[/bold cyan]\n")
    
    # Configuration
    input_file = "sample/input_eligibility_multiple.json"
    output_file = f"sample/output_multiple_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    console.print(f"[cyan]📂 Input file:[/cyan] {input_file}")
    console.print(f"[cyan]📂 Output file:[/cyan] {output_file}")
    console.print()
    
    # Validate settings
    if not settings.availity_username or not settings.availity_password:
        console.print("[bold red]ERROR: Missing credentials in .env file[/bold red]")
        console.print("Please set AVAILITY_USERNAME and AVAILITY_PASSWORD")
        return 1
    
    results: List[EligibilityResult] = []
    errors: List[dict] = []
    
    try:
        # Load requests
        console.print("[yellow]Loading requests from JSON...[/yellow]")
        requests_data = load_requests_from_json(input_file)
        console.print(f"[green]✓ Loaded {len(requests_data)} requests[/green]\n")
        
        # Create EligibilityRequest objects
        requests = []
        for i, req_data in enumerate(requests_data, 1):
            try:
                req = create_eligibility_request(req_data)
                requests.append(req)
                console.print(f"  [cyan]{i}.[/cyan] Request ID: {req.request_id} | Payer: {req.payer_name} | Member: {req.member_id}")
            except Exception as e:
                console.print(f"  [red]{i}. ERROR validating request: {e}[/red]")
                errors.append({
                    "request_id": req_data.get("request_id", "unknown"),
                    "error_type": "ValidationError",
                    "error_message": str(e)
                })
        
        if not requests:
            console.print("[bold red]No valid requests to process![/bold red]")
            return 1
        
        console.print(f"\n[bold green]Processing {len(requests)} requests...[/bold green]\n")
        
        # Process requests with bot
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task(
                "[cyan]Processing eligibility requests...",
                total=len(requests)
            )
            
            # Initialize bot (reuse same session for all requests)
            with EligibilityBot(
                base_url=settings.availity_base_url,
                username=settings.availity_username,
                password=settings.availity_password,
                headless=False,  # Set to False to watch the process
                artifacts_dir="artifacts"
            ) as bot:
                
                # Login once
                try:
                    bot.login()
                except Exception as e:
                    console.print(f"[bold red]✗ Login failed: {e}[/bold red]")
                    return 1
                
                # Process each request
                for i, request in enumerate(requests, 1):
                    progress.update(
                        task,
                        description=f"[cyan]Processing request {i}/{len(requests)} (ID: {request.request_id})..."
                    )
                    
                    try:
                        result = bot.process_request(request)
                        results.append(result)
                        logger.info(f"✓ Success: Request {request.request_id}")
                        
                    except Exception as e:
                        error_type = type(e).__name__
                        error_msg = str(e)
                        logger.error(f"✗ Failed: Request {request.request_id} - {error_type}: {error_msg}")
                        
                        errors.append({
                            "request_id": request.request_id,
                            "error_type": error_type,
                            "error_message": error_msg
                        })
                    
                    progress.update(task, advance=1)
        
        # Display results
        console.print("\n[bold cyan]═══════════════════ RESULTS ═══════════════════[/bold cyan]\n")
        console.print(f"[green]✓ Successful:[/green] {len(results)}/{len(requests)}")
        console.print(f"[red]✗ Failed:[/red] {len(errors)}/{len(requests)}")
        
        display_results_table(results, errors)
        
        # Save results
        if results or errors:
            console.print()
            all_results = results.copy()
            
            # Add error entries to results
            for error in errors:
                error_result = EligibilityResult(
                    request_id=error["request_id"],
                    coverage_status=f"ERROR: {error['error_type']}",
                    plan_name=error["error_message"],
                    plan_type=None,
                    coverage_start_date=None,
                    coverage_end_date=None,
                    benefit_lines=[]
                )
                all_results.append(error_result)
            
            save_results_to_json(all_results, output_file)
        
        console.print("\n[bold green]✓ Test completed![/bold green]\n")
        
        return 0 if len(errors) == 0 else 1
        
    except FileNotFoundError as e:
        console.print(f"[bold red]ERROR: {e}[/bold red]")
        console.print(f"[yellow]Please ensure the input file exists: {input_file}[/yellow]")
        return 1
        
    except json.JSONDecodeError as e:
        console.print(f"[bold red]ERROR: Invalid JSON file[/bold red]")
        console.print(f"[red]{e}[/red]")
        return 1
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
        return 1
        
    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[bold red]ERROR: {e}[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
