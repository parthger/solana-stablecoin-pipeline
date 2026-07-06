# Solana Stablecoin Pipeline

Medallion architecture pipeline tracking USDC and PYUSD flows on Solana. Demonstrates instruction decoding, CPI handling, and cross-ecosystem stablecoin analytics.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Helius API    │────▶│   Bronze Layer  │────▶│   Silver Layer  │
│  (Data Source)  │     │  (Raw Txs/dlt)  │     │ (Decoded/dbt)   │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌─────────────────┐              │
                        │   Gold Layer    │◀─────────────┘
                        │  (Metrics/dbt)  │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   Streamlit     │
                        │   Dashboard     │
                        └─────────────────┘
```

## The Credential: Instruction Decoding

The core challenge in Solana data engineering is decoding packed transactions with nested CPIs. This pipeline handles:

- **SPL Token instruction parsing** (Transfer, MintTo, Burn + Checked variants)
- **CPI tree walking** with depth tracking
- **Context classification** (direct transfer vs DEX swap vs bridge)
- **Address lookup table resolution** for V0 transactions

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/solana-stablecoin-pipeline
cd solana-stablecoin-pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev,dashboard]"

# Configure API key
cp .env.example .env
# Edit .env and add your HELIUS_API_KEY

# Run backfill (7 days)
./scripts/run_backfill.sh 7

# Or run steps individually:
python -m src.ingest.cli backfill --days 7
cd transform && dbt run && cd ..

# Launch dashboard
streamlit run app/dashboard.py
```

## Project Structure

```
solana-stablecoin-pipeline/
├── src/
│   ├── config.py           # Settings, constants, program IDs
│   ├── ingest/
│   │   ├── client.py       # Helius API client
│   │   ├── backfill.py     # Historical data ingestion
│   │   └── cli.py          # CLI commands
│   ├── decode/
│   │   ├── models.py       # Pydantic models for events
│   │   └── decoder.py      # SPL Token instruction decoder
│   └── utils/
│       └── labels.py       # Wallet labeling
├── transform/
│   ├── dbt_project.yml
│   └── models/
│       ├── staging/        # Views over bronze
│       ├── silver/         # Decoded events
│       └── gold/           # Aggregated metrics
├── app/
│   └── dashboard.py        # Streamlit dashboard
├── tests/
│   └── test_decoder.py     # Decoder unit tests
└── scripts/
    └── run_backfill.sh     # Full pipeline script
```

## Data Models

### Bronze (Raw)
- `transactions`: Raw Solana transactions from Helius

### Silver (Decoded)
- `stablecoin_transfers`: Decoded transfer events with owner resolution
- `stablecoin_mints`: Supply expansion events
- `stablecoin_burns`: Supply contraction events

### Gold (Aggregated)
- `daily_stablecoin_flows`: Daily volume, count, unique addresses
- `holder_concentration`: Top holder %, Gini coefficient, tier distribution

## Key Metrics for Moat Research

This pipeline feeds directly into stablecoin moat analysis:

| Metric | Description |
|--------|-------------|
| `top_10_pct` | % of supply held by top 10 holders |
| `holder_count` | Total unique holders |
| `velocity` | Transfer volume / total supply |
| `large_transfer_volume` | Whale activity ($100K+ transfers) |

## Extending

### Add New Stablecoins

1. Add mint address to `src/config.py`:
   ```python
   NEW_MINT = "NewMintAddress..."
   TARGET_MINTS.add(NEW_MINT)
   TOKEN_METADATA[NEW_MINT] = {"symbol": "NEW", "decimals": 6}
   ```

2. Update dbt vars in `transform/dbt_project.yml`

### Add Real-Time Streaming

Install streaming dependencies:
```bash
pip install -e ".[streaming]"
```

See `src/ingest/stream.py` (coming soon) for Yellowstone gRPC integration.

## Cross-Ecosystem Integration

This pipeline is part of a broader stablecoin analytics suite:

| Pipeline | Chain | Focus |
|----------|-------|-------|
| AUSD Pipeline | EVM | Agora stablecoin |
| BigQuery Flow Tracker | EVM | Movement patterns |
| **This Pipeline** | Solana | USDC/PYUSD flows |

The `cross_ecosystem_summary` gold table enables unified analysis across all chains.

## License

MIT
