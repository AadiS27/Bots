"""Script to verify and analyze test results from multiple eligibility requests."""

import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def load_json_file(filepath: str):
    """Load JSON file."""
    path = Path(filepath)
    if not path.exists():
        return None
    
    with open(path, 'r') as f:
        return json.load(f)


def analyze_single_result(result: dict) -> dict:
    """Analyze a single result and return status."""
    request_id = result.get('request_id', 'unknown')
    coverage_status = result.get('coverage_status')
    plan_name = result.get('plan_name')
    benefit_lines = result.get('benefit_lines', [])
    
    # Determine result status
    if coverage_status and plan_name:
        status = "✓ SUCCESS"
        status_color = "green"
    elif coverage_status is None and plan_name is None:
        status = "✗ FAILED (No Data)"
        status_color = "red"
    elif coverage_status and coverage_status.startswith("ERROR"):
        status = f"✗ ERROR: {plan_name or 'Unknown'}"
        status_color = "yellow"
    else:
        status = "⚠ PARTIAL"
        status_color = "yellow"
    
    return {
        'request_id': request_id,
        'status': status,
        'status_color': status_color,
        'coverage_status': coverage_status or 'N/A',
        'plan_name': plan_name or 'N/A',
        'plan_type': result.get('plan_type') or 'N/A',
        'benefit_count': len(benefit_lines),
        'has_dates': bool(result.get('coverage_start_date') or result.get('coverage_end_date')),
        'has_deductible': result.get('deductible_individual') is not None,
        'html_saved': bool(result.get('raw_response_html_path'))
    }


def display_results_table(results: list):
    """Display results in a formatted table."""
    table = Table(
        title="📊 Multiple Eligibility Test Results",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Request ID", justify="center", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Coverage", justify="left")
    table.add_column("Plan Name", justify="left", max_width=30)
    table.add_column("Plan Type", justify="center")
    table.add_column("Benefits", justify="center")
    table.add_column("Dates", justify="center")
    table.add_column("Deductible", justify="center")
    table.add_column("HTML", justify="center")
    
    success_count = 0
    partial_count = 0
    failed_count = 0
    
    for analysis in results:
        # Count results
        if "SUCCESS" in analysis['status']:
            success_count += 1
        elif "FAILED" in analysis['status']:
            failed_count += 1
        else:
            partial_count += 1
        
        # Format row
        table.add_row(
            str(analysis['request_id']),
            f"[{analysis['status_color']}]{analysis['status']}[/{analysis['status_color']}]",
            analysis['coverage_status'][:20],
            analysis['plan_name'][:30],
            analysis['plan_type'],
            f"[cyan]{analysis['benefit_count']}[/cyan]" if analysis['benefit_count'] > 0 else "[dim]0[/dim]",
            "[green]✓[/green]" if analysis['has_dates'] else "[dim]✗[/dim]",
            "[green]✓[/green]" if analysis['has_deductible'] else "[dim]✗[/dim]",
            "[green]✓[/green]" if analysis['html_saved'] else "[dim]✗[/dim]"
        )
    
    console.print("\n")
    console.print(table)
    
    # Summary
    total = len(results)
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  [green]✓ Success:[/green] {success_count}/{total}")
    if partial_count > 0:
        console.print(f"  [yellow]⚠ Partial:[/yellow] {partial_count}/{total}")
    if failed_count > 0:
        console.print(f"  [red]✗ Failed:[/red] {failed_count}/{total}")
    
    return success_count, partial_count, failed_count


def display_detailed_result(result: dict):
    """Display detailed information for a single result."""
    console.print(f"\n[bold cyan]Request ID: {result.get('request_id')}[/bold cyan]")
    console.print(f"  Coverage Status: {result.get('coverage_status', 'N/A')}")
    console.print(f"  Plan Name: {result.get('plan_name', 'N/A')}")
    console.print(f"  Plan Type: {result.get('plan_type', 'N/A')}")
    console.print(f"  Coverage Dates: {result.get('coverage_start_date', 'N/A')} to {result.get('coverage_end_date', 'N/A')}")
    console.print(f"  Deductible (Individual): ${result.get('deductible_individual', 0):,.2f}")
    console.print(f"  Deductible Remaining: ${result.get('deductible_remaining_individual', 0):,.2f}")
    console.print(f"  OOP Max (Individual): ${result.get('oop_max_individual', 0):,.2f}")
    console.print(f"  OOP Max (Family): ${result.get('oop_max_family', 0):,.2f}")
    
    benefit_lines = result.get('benefit_lines', [])
    if benefit_lines:
        console.print(f"\n  [bold]Benefits ({len(benefit_lines)}):[/bold]")
        for i, benefit in enumerate(benefit_lines[:5], 1):  # Show first 5
            console.print(f"    {i}. {benefit.get('benefit_category', 'Unknown')}")
            if benefit.get('copay_amount'):
                console.print(f"       Copay: ${benefit['copay_amount']:.2f}")
            if benefit.get('coinsurance_percent'):
                console.print(f"       Coinsurance: {benefit['coinsurance_percent']}%")
        if len(benefit_lines) > 5:
            console.print(f"    ... and {len(benefit_lines) - 5} more")
    
    if result.get('raw_response_html_path'):
        console.print(f"\n  [dim]HTML Response: {result['raw_response_html_path']}[/dim]")


def main():
    """Main function."""
    console.print("\n[bold green]═══════════════════════════════════════════[/bold green]")
    console.print("[bold green]   Multiple Eligibility Test Verification  [/bold green]")
    console.print("[bold green]═══════════════════════════════════════════[/bold green]\n")
    
    # Test files to check
    test_files = [
        "sample/output_multiple_test.json",
        "sample/output_multiple_final.json",
        "sample/output_multiple_optimized.json",
        "sample/output_multiple_fixed.json",
    ]
    
    console.print("[cyan]Looking for test result files...[/cyan]\n")
    
    results_found = []
    for filepath in test_files:
        data = load_json_file(filepath)
        if data:
            console.print(f"  [green]✓[/green] Found: {filepath}")
            results_found.append((filepath, data))
        else:
            console.print(f"  [dim]✗ Not found: {filepath}[/dim]")
    
    if not results_found:
        console.print("\n[yellow]No test result files found![/yellow]")
        console.print("\n[bold]Expected files:[/bold]")
        for filepath in test_files:
            console.print(f"  • {filepath}")
        console.print("\n[bold]To run the test:[/bold]")
        console.print("  [cyan]$env:PYTHONPATH=\"e:\\QuickIntell11\\bots\"[/cyan]")
        console.print("  [cyan]python scripts/run_eligibility.py --input sample/input_eligibility_multiple.json --output sample/output_multiple_test.json --no-headless[/cyan]")
        return
    
    # Analyze each results file
    for filepath, data in results_found:
        console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
        console.print(f"[bold cyan]File: {filepath}[/bold cyan]")
        console.print(f"[bold cyan]{'='*60}[/bold cyan]")
        
        # Handle both single object and array
        if isinstance(data, dict):
            results = [data]
        elif isinstance(data, list):
            results = data
        else:
            console.print("[red]Invalid JSON format[/red]")
            continue
        
        # Analyze each result
        analyses = [analyze_single_result(r) for r in results]
        
        # Display table
        success, partial, failed = display_results_table(analyses)
        
        # Show detailed view for successful results
        if success > 0:
            console.print("\n[bold]Detailed Results (Successful):[/bold]")
            for result in results:
                analysis = analyze_single_result(result)
                if "SUCCESS" in analysis['status']:
                    display_detailed_result(result)
    
    console.print("\n[bold green]✓ Verification complete![/bold green]\n")


if __name__ == "__main__":
    main()
