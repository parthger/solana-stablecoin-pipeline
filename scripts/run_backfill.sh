#!/bin/bash
# Backfill historical data and run transformations

set -e

DAYS=${1:-7}

echo "=== Solana Stablecoin Pipeline ==="
echo "Backfilling $DAYS days of data..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run ingestion
echo ""
echo "1. Running ingestion..."
python -m src.ingest.cli backfill --days "$DAYS"

# Run dbt transformations
echo ""
echo "2. Running dbt transformations..."
cd transform
dbt run --profiles-dir .
dbt test --profiles-dir .
cd ..

echo ""
echo "=== Pipeline complete ==="
echo ""
echo "To view the dashboard:"
echo "  streamlit run app/dashboard.py"
