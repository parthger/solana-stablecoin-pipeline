"""CLI for ingestion commands."""

import asyncio
from datetime import datetime

import typer
import structlog

from src.ingest.backfill import backfill_transactions

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

app = typer.Typer(help="Solana stablecoin pipeline ingestion CLI")


@app.command()
def backfill(
    days: int = typer.Option(7, help="Number of days to backfill"),
    database_url: str | None = typer.Option(None, help="Database URL override"),
    max_batches: int = typer.Option(0, help="Max batches per token (0=unlimited)"),
):
    """Backfill historical transactions."""
    asyncio.run(backfill_transactions(days=days, database_url=database_url, max_batches=max_batches))


@app.command()
def snapshot(
    mint: str = typer.Option(None, help="Specific mint to snapshot (default: all)"),
):
    """Take a snapshot of current token holders."""
    typer.echo("Snapshot not yet implemented")
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
