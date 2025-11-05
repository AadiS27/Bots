"""Script to display data from the database."""

import asyncio
import sys
from datetime import datetime

from rich.console import Console
from rich.table import Table
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from db import get_session
from db.models import EligibilityRequest, EligibilityResult, EligibilityBenefitLine, Payer, Patient

console = Console()


async def show_requests():
    """Show all eligibility requests."""
    async with get_session() as session:
        result = await session.execute(
            select(EligibilityRequest)
            .options(selectinload(EligibilityRequest.payer))
            .order_by(EligibilityRequest.id.desc())
            .limit(10)
        )
        requests = result.scalars().all()

        if not requests:
            console.print("[yellow]No requests found in database[/yellow]\n")
            return

        table = Table(title="Eligibility Requests", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Payer ID", style="green")
        table.add_column("Member ID", style="yellow")
        table.add_column("DOS", style="blue")
        table.add_column("Status", style="red")
        table.add_column("Error", style="red", max_width=50)
        table.add_column("Created", style="dim")

        for req in requests:
            payer_name = str(req.payer_id) if req.payer_id else "N/A"
            if req.payer:
                payer_name = f"{req.payer.name} (ID: {req.payer_id})"

            error_msg = req.last_error_message or ""
            if len(error_msg) > 50:
                error_msg = error_msg[:47] + "..."

            table.add_row(
                str(req.id),
                payer_name,
                req.member_id,
                str(req.dos_from),
                req.status,
                error_msg,
                req.created_at.strftime("%Y-%m-%d %H:%M") if req.created_at else "N/A"
            )

        console.print(table)
        console.print()


async def show_results():
    """Show all eligibility results."""
    async with get_session() as session:
        result = await session.execute(
            select(EligibilityResult)
            .order_by(EligibilityResult.id.desc())
            .limit(10)
        )
        results = result.scalars().all()

        if not results:
            console.print("[yellow]No results found in database[/yellow]\n")
            return

        table = Table(title="Eligibility Results", show_header=True, header_style="bold magenta")
        table.add_column("Request ID", style="cyan")
        table.add_column("Coverage Status", style="green")
        table.add_column("Plan Name", style="yellow", max_width=30)
        table.add_column("Plan Type", style="blue", max_width=20)
        table.add_column("Start Date", style="dim")
        table.add_column("End Date", style="dim")
        table.add_column("Created", style="dim")

        for res in results:
            plan_name = res.plan_name or "N/A"
            if len(plan_name) > 30:
                plan_name = plan_name[:27] + "..."

            table.add_row(
                str(res.eligibility_request_id),
                res.coverage_status or "N/A",
                plan_name,
                res.plan_type or "N/A",
                str(res.coverage_start_date) if res.coverage_start_date else "N/A",
                str(res.coverage_end_date) if res.coverage_end_date else "N/A",
                res.created_at.strftime("%Y-%m-%d %H:%M") if res.created_at else "N/A"
            )

        console.print(table)
        console.print()


async def show_payers():
    """Show all payers."""
    async with get_session() as session:
        result = await session.execute(select(Payer).order_by(Payer.id))
        payers = result.scalars().all()

        if not payers:
            console.print("[yellow]No payers found in database[/yellow]\n")
            return

        table = Table(title="Payers", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Created", style="dim")

        for payer in payers:
            table.add_row(
                str(payer.id),
                payer.name,
                payer.created_at.strftime("%Y-%m-%d %H:%M") if payer.created_at else "N/A"
            )

        console.print(table)
        console.print()


async def show_patients():
    """Show all patients."""
    async with get_session() as session:
        result = await session.execute(select(Patient).order_by(Patient.id.desc()).limit(10))
        patients = result.scalars().all()

        if not patients:
            console.print("[yellow]No patients found in database[/yellow]\n")
            return

        table = Table(title="Patients", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("First Name", style="green")
        table.add_column("Last Name", style="green")
        table.add_column("DOB", style="blue")
        table.add_column("Created", style="dim")

        for patient in patients:
            table.add_row(
                str(patient.id),
                patient.first_name or "N/A",
                patient.last_name,
                str(patient.date_of_birth) if patient.date_of_birth else "N/A",
                patient.created_at.strftime("%Y-%m-%d %H:%M") if patient.created_at else "N/A"
            )

        console.print(table)
        console.print()


async def show_stats():
    """Show database statistics."""
    async with get_session() as session:
        # Count requests by status
        result = await session.execute(
            text("""
                SELECT status, COUNT(*) as count 
                FROM eligibility_requests 
                GROUP BY status
            """)
        )
        status_counts = result.fetchall()

        table = Table(title="Request Statistics", show_header=True, header_style="bold magenta")
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="green")

        for status, count in status_counts:
            table.add_row(status, str(count))

        console.print(table)
        console.print()


async def main():
    """Main function."""
    console.print("\n[bold green]Database Data Viewer[/bold green]\n")

    try:
        await show_stats()
        await show_requests()
        await show_results()
        await show_payers()
        await show_patients()

        return 0

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

