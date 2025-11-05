"""Test script to enqueue and process multiple eligibility requests."""

import asyncio
import sys
from datetime import date, datetime

from loguru import logger
from rich.console import Console

from config import settings
from db import get_session
from db.repo_eligibility import ensure_payer, ensure_patient, enqueue_eligibility_request, get_next_pending_request

console = Console()


async def enqueue_multiple_requests():
    """Enqueue multiple test requests."""
    console.print("\n[bold cyan]Enqueuing Multiple Test Requests[/bold cyan]\n")

    async with get_session() as session:
        # Ensure payer exists
        payer = await ensure_payer(session, name="CIGNA HEALTHCARE")

        # Create multiple test requests with different member IDs
        test_requests = [
            {
                "member_id": "TEST001",
                "patient_first_name": "JOHN",
                "patient_last_name": "DOE",
                "dob": date(1987, 6, 15),
                "dos_from": date(2025, 11, 5),
                "service_type_code": "30",
            },
            {
                "member_id": "TEST002",
                "patient_first_name": "JANE",
                "patient_last_name": "SMITH",
                "dob": date(1990, 3, 20),
                "dos_from": date(2025, 11, 6),
                "service_type_code": None,
            },
            {
                "member_id": "TEST003",
                "patient_first_name": "BOB",
                "patient_last_name": "JOHNSON",
                "dob": date(1985, 12, 10),
                "dos_from": date(2025, 11, 7),
                "service_type_code": "30",
            },
        ]

        request_ids = []
        for i, req_data in enumerate(test_requests, 1):
            console.print(f"[cyan]Enqueuing request {i}/{len(test_requests)}...[/cyan]")
            
            # Ensure patient exists
            patient = await ensure_patient(
                session,
                first_name=req_data["patient_first_name"],
                last_name=req_data["patient_last_name"],
                date_of_birth=req_data["dob"],
            )

            # Enqueue request
            request_id = await enqueue_eligibility_request(
                session,
                payer_id=payer.id,
                patient_id=patient.id,
                member_id=req_data["member_id"],
                dos_from=req_data["dos_from"],
                service_type_code=req_data["service_type_code"],
            )
            
            request_ids.append(request_id)
            console.print(f"[green]  -> Request ID: {request_id} (Member: {req_data['member_id']})[/green]")

        await session.commit()
        console.print(f"\n[bold green]SUCCESS: Enqueued {len(request_ids)} requests[/bold green]")
        console.print(f"[cyan]Request IDs: {request_ids}[/cyan]\n")
        
        return request_ids


async def main():
    """Main function."""
    console.print("\n[bold green]Multiple Requests Test Script[/bold green]\n")
    
    try:
        # Enqueue multiple requests
        request_ids = await enqueue_multiple_requests()
        
        console.print("[bold cyan]Next Steps:[/bold cyan]")
        console.print("  • Run the bot multiple times to process all requests:")
        console.print("    [green]python scripts/run_eligibility.py --db --no-headless[/green]")
        console.print("  • Or check pending requests:")
        console.print("    [green]python scripts/show_db_data.py[/green]")
        console.print()
        
        return 0

    except Exception as e:
        logger.exception("Failed to enqueue requests")
        console.print(f"[bold red]Error: {e}[/bold red]")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

