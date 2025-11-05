"""Enqueue a sample eligibility request from JSON file."""

import asyncio
import json
import sys
from datetime import date, datetime
from pathlib import Path

from loguru import logger
from rich.console import Console

from config import settings
from db import get_session
from db.repo_eligibility import ensure_payer, ensure_patient, enqueue_eligibility_request

console = Console()


def parse_date(date_str: str) -> date:
    """Parse date string in ISO format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


async def enqueue_from_json(json_path: Path) -> int:
    """
    Read JSON file and enqueue eligibility request.

    Args:
        json_path: Path to input JSON file

    Returns:
        Created request ID
    """
    # Load JSON
    console.print(f"\n[cyan]Reading input file:[/cyan] {json_path}")
    data = json.loads(json_path.read_text())

    async with get_session() as session:
        # Ensure payer exists
        console.print(f"[cyan]Ensuring payer:[/cyan] {data['payer_name']}")
        payer = await ensure_payer(session, name=data["payer_name"])

        # Ensure patient exists
        console.print(f"[cyan]Ensuring patient:[/cyan] {data['patient_last_name']}, {data.get('patient_first_name', 'N/A')}")
        patient = await ensure_patient(
            session,
            first_name=data.get("patient_first_name", ""),
            last_name=data["patient_last_name"],
            date_of_birth=parse_date(data["dob"]),
            external_patient_id=None,  # No external ID from sample
        )

        # Enqueue eligibility request
        console.print("[cyan]Enqueuing eligibility request...[/cyan]")
        request_id = await enqueue_eligibility_request(
            session,
            payer_id=payer.id,
            patient_id=patient.id,
            member_id=data["member_id"],
            dos_from=parse_date(data["dos_from"]),
            dos_to=parse_date(data["dos_to"]) if data.get("dos_to") else None,
            service_type_code=data.get("service_type_code"),
            group_number=None,
        )

        await session.commit()

        console.print(f"[bold green]SUCCESS: Enqueued request ID: {request_id}[/bold green]\n")
        return request_id


async def main() -> int:
    """Main function."""
    console.print("\n[bold green]Enqueue Sample Eligibility Request[/bold green]\n")

    # Default to sample input file
    json_path = Path("sample/input_eligibility.json")

    if not json_path.exists():
        console.print(f"[bold red]Error: Input file not found: {json_path}[/bold red]")
        return 1

    try:
        request_id = await enqueue_from_json(json_path)

        console.print("[bold cyan]Next steps:[/bold cyan]")
        console.print(f"  • Run the bot: [green]python scripts/run_eligibility.py --db[/green]")
        console.print(f"  • Check status in database: [green]SELECT * FROM eligibility_requests WHERE id = {request_id};[/green]")
        console.print()

        return 0

    except Exception as e:
        logger.exception("Failed to enqueue request")
        console.print(f"[bold red]Error: {e}[/bold red]")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

