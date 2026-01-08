"""
CLI entry point for DRI Tracker.

Usage:
    python -m dri ingest --date 2025-01-15
    python -m dri compute --date 2025-01-15
    python -m dri daily_job
"""

import asyncio
import click
from datetime import date, timedelta
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def cli():
    """DRI Tracker CLI."""
    pass


@cli.command()
@click.option("--date", "target_date", type=click.DateTime(formats=["%Y-%m-%d"]), required=True)
def ingest(target_date):
    """Ingest data for a specific date."""
    from dri.jobs import run_ingest
    
    target = target_date.date()
    console.print(f"[bold blue]Ingesting data for {target}...[/bold blue]")
    
    asyncio.run(run_ingest(target))
    
    console.print("[bold green]Ingestion complete![/bold green]")


@cli.command()
@click.option("--date", "target_date", type=click.DateTime(formats=["%Y-%m-%d"]), required=True)
def compute(target_date):
    """Compute DRI for a specific date."""
    from dri.jobs import run_compute
    
    target = target_date.date()
    console.print(f"[bold blue]Computing DRI for {target}...[/bold blue]")
    
    result = asyncio.run(run_compute(target))
    
    if result:
        table = Table(title=f"DRI Results for {target}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("DRI", f"{result.dri:.2f}")
        table.add_row("V_score", f"{result.v_score:.2f}")
        table.add_row("R_score", f"{result.r_score:.2f}")
        table.add_row("S_score", f"{result.s_score:.2f}")
        table.add_row("P_score", f"{result.p_score:.2f}")
        table.add_row("Quality", result.data_quality.overall_quality)
        table.add_row("Is Spike", str(result.is_spike))
        
        console.print(table)
    else:
        console.print("[bold red]Failed to compute DRI[/bold red]")


@cli.command()
def daily_job():
    """Run daily ingest and compute for yesterday."""
    from dri.jobs import run_ingest, run_compute
    
    yesterday = date.today() - timedelta(days=1)
    console.print(f"[bold blue]Running daily job for {yesterday}...[/bold blue]")
    
    console.print("[yellow]Step 1: Ingesting data...[/yellow]")
    asyncio.run(run_ingest(yesterday))
    
    console.print("[yellow]Step 2: Computing DRI...[/yellow]")
    result = asyncio.run(run_compute(yesterday))
    
    if result:
        console.print(f"[bold green]Daily job complete! DRI = {result.dri:.2f}[/bold green]")
    else:
        console.print("[bold red]Daily job failed[/bold red]")


@cli.command()
def seed():
    """Seed demo data for development."""
    from dri.seed import seed_demo_data
    
    console.print("[bold blue]Seeding demo data...[/bold blue]")
    asyncio.run(seed_demo_data())
    console.print("[bold green]Demo data seeded![/bold green]")


if __name__ == "__main__":
    cli()


