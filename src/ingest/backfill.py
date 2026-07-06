"""Backfill historical transactions to bronze layer."""

import asyncio
from datetime import datetime, timedelta, timezone

import dlt
import structlog
from dlt.sources.helpers import requests

from src.config import Settings, USDC_MINT, PYUSD_MINT, TOKEN_METADATA
from src.ingest.client import HeliusClient, is_stablecoin_transaction

logger = structlog.get_logger()


@dlt.source
def solana_stablecoins(
    settings: Settings,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    """DLT source for Solana stablecoin transactions."""

    @dlt.resource(
        name="transactions",
        write_disposition="merge",
        primary_key="signature",
    )
    def transactions():
        """Yield stablecoin transactions."""
        yield from _fetch_transactions_sync(settings, start_date, end_date)

    return transactions


def _fetch_transactions_sync(
    settings: Settings,
    start_date: datetime | None,
    end_date: datetime | None,
) -> list[dict]:
    """Synchronous wrapper for transaction fetching (dlt requirement)."""
    return asyncio.run(_fetch_transactions(settings, start_date, end_date))


async def _fetch_transactions(
    settings: Settings,
    start_date: datetime | None,
    end_date: datetime | None,
) -> list[dict]:
    """Fetch transactions for all target mints."""
    all_transactions = []

    async with HeliusClient(settings) as client:
        for mint in [USDC_MINT, PYUSD_MINT]:
            token_info = TOKEN_METADATA[mint]
            logger.info(f"Fetching transactions for {token_info['symbol']}")

            cursor = None
            batch_count = 0

            while True:
                # Fetch batch of transactions
                txs = await client.get_signatures_for_address(
                    address=mint,
                    before=cursor,
                    limit=100,
                )

                if not txs:
                    break

                # Filter by date if specified
                filtered = []
                for tx in txs:
                    tx_time = datetime.fromtimestamp(tx.get("timestamp", 0), tz=timezone.utc)

                    if end_date and tx_time > end_date:
                        continue
                    if start_date and tx_time < start_date:
                        break

                    if is_stablecoin_transaction(tx):
                        filtered.append(_transform_to_bronze(tx, mint))

                all_transactions.extend(filtered)
                batch_count += 1

                # Check if we've gone past start_date
                if txs:
                    last_time = datetime.fromtimestamp(
                        txs[-1].get("timestamp", 0), tz=timezone.utc
                    )
                    if start_date and last_time < start_date:
                        break

                    cursor = txs[-1].get("signature")

                logger.info(
                    f"Fetched batch {batch_count}",
                    mint=token_info["symbol"],
                    count=len(filtered),
                    total=len(all_transactions),
                )

                # Rate limiting
                await asyncio.sleep(0.1)

    return all_transactions


def _transform_to_bronze(tx: dict, source_mint: str) -> dict:
    """Transform Helius response to bronze schema."""
    return {
        "signature": tx.get("signature"),
        "slot": tx.get("slot"),
        "block_time": datetime.fromtimestamp(tx.get("timestamp", 0), tz=timezone.utc),
        "fee": tx.get("fee"),
        "fee_payer": tx.get("feePayer"),
        "success": tx.get("transactionError") is None,
        # Raw data for later decoding
        "source": tx.get("source"),
        "type": tx.get("type"),
        "description": tx.get("description"),
        # Token transfers (Helius pre-parsed)
        "token_transfers": tx.get("tokenTransfers", []),
        "native_transfers": tx.get("nativeTransfers", []),
        # Account data for balance changes
        "account_data": tx.get("accountData", []),
        # Instructions (raw for our decoder)
        "instructions": tx.get("instructions", []),
        # Metadata
        "source_mint": source_mint,
        "ingested_at": datetime.now(timezone.utc),
    }


async def backfill_transactions(
    days: int = 7,
    database_url: str | None = None,
) -> None:
    """Run backfill for the specified number of days."""
    settings = Settings()

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    logger.info(
        "Starting backfill",
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    # Configure dlt pipeline
    pipeline = dlt.pipeline(
        pipeline_name="solana_stablecoins",
        destination="duckdb",
        dataset_name="bronze",
    )

    # Run the pipeline
    source = solana_stablecoins(settings, start_date, end_date)
    info = pipeline.run(source)

    logger.info("Backfill complete", info=str(info))


if __name__ == "__main__":
    asyncio.run(backfill_transactions(days=7))
