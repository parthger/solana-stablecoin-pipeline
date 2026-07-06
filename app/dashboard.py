"""Streamlit dashboard for Solana stablecoin analytics."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Solana Stablecoin Flows",
    page_icon="💵",
    layout="wide",
)

# Database connection
DB_PATH = Path(__file__).parent.parent / "data" / "pipeline.duckdb"


@st.cache_resource
def get_connection():
    """Get DuckDB connection."""
    return duckdb.connect(str(DB_PATH), read_only=True)


def load_daily_flows() -> pd.DataFrame:
    """Load daily flow metrics."""
    conn = get_connection()
    query = """
        SELECT *
        FROM gold.daily_stablecoin_flows
        ORDER BY date DESC
        LIMIT 90
    """
    try:
        return conn.execute(query).fetchdf()
    except Exception:
        return pd.DataFrame()


def load_holder_concentration() -> pd.DataFrame:
    """Load holder concentration metrics."""
    conn = get_connection()
    query = """
        SELECT *
        FROM gold.holder_concentration
        ORDER BY snapshot_date DESC
        LIMIT 30
    """
    try:
        return conn.execute(query).fetchdf()
    except Exception:
        return pd.DataFrame()


def load_recent_transfers(limit: int = 100) -> pd.DataFrame:
    """Load recent transfers."""
    conn = get_connection()
    query = f"""
        SELECT
            signature,
            block_time,
            token_symbol,
            source_owner,
            destination_owner,
            amount_decimal
        FROM silver.stablecoin_transfers
        ORDER BY block_time DESC
        LIMIT {limit}
    """
    try:
        return conn.execute(query).fetchdf()
    except Exception:
        return pd.DataFrame()


# Header
st.title("🪙 Solana Stablecoin Flows")
st.markdown("Real-time analytics for USDC and PYUSD on Solana")

# Sidebar
st.sidebar.header("Filters")
token_filter = st.sidebar.multiselect(
    "Token",
    options=["USDC", "PYUSD"],
    default=["USDC", "PYUSD"],
)

# Load data
daily_flows = load_daily_flows()
holder_data = load_holder_concentration()
recent_transfers = load_recent_transfers()

# Check if data exists
if daily_flows.empty:
    st.warning(
        "No data available. Run the pipeline first:\n\n"
        "```bash\n"
        "python -m src.ingest.backfill --days 7\n"
        "cd transform && dbt run\n"
        "```"
    )
    st.stop()

# Filter data
if token_filter:
    daily_flows = daily_flows[daily_flows["token_symbol"].isin(token_filter)]
    if not holder_data.empty:
        holder_data = holder_data[holder_data["token_symbol"].isin(token_filter)]
    if not recent_transfers.empty:
        recent_transfers = recent_transfers[recent_transfers["token_symbol"].isin(token_filter)]

# KPIs
st.subheader("Key Metrics (Last 24h)")
col1, col2, col3, col4 = st.columns(4)

if not daily_flows.empty:
    latest = daily_flows.iloc[0] if len(daily_flows) > 0 else {}

    with col1:
        st.metric(
            "Transfer Volume",
            f"${latest.get('transfer_volume', 0):,.0f}",
        )

    with col2:
        st.metric(
            "Transfer Count",
            f"{latest.get('transfer_count', 0):,}",
        )

    with col3:
        st.metric(
            "Unique Senders",
            f"{latest.get('unique_senders', 0):,}",
        )

    with col4:
        st.metric(
            "Unique Receivers",
            f"{latest.get('unique_receivers', 0):,}",
        )

# Charts
st.subheader("Daily Transfer Volume")

if not daily_flows.empty:
    fig_volume = px.area(
        daily_flows.sort_values("date"),
        x="date",
        y="transfer_volume",
        color="token_symbol",
        title="Daily Stablecoin Volume on Solana",
        labels={"transfer_volume": "Volume (USD)", "date": "Date"},
    )
    fig_volume.update_layout(hovermode="x unified")
    st.plotly_chart(fig_volume, use_container_width=True)

# Two columns for additional charts
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Transfer Count")
    if not daily_flows.empty:
        fig_count = px.line(
            daily_flows.sort_values("date"),
            x="date",
            y="transfer_count",
            color="token_symbol",
            markers=True,
        )
        st.plotly_chart(fig_count, use_container_width=True)

with col_right:
    st.subheader("Unique Addresses")
    if not daily_flows.empty:
        fig_addresses = px.bar(
            daily_flows.sort_values("date"),
            x="date",
            y="unique_addresses",
            color="token_symbol",
            barmode="group",
        )
        st.plotly_chart(fig_addresses, use_container_width=True)

# Holder concentration (for moat research)
st.subheader("Holder Concentration (Moat Metrics)")

if not holder_data.empty:
    col1, col2 = st.columns(2)

    with col1:
        # Top holder percentages
        latest_holder = holder_data.groupby("token_symbol").first().reset_index()

        fig_concentration = go.Figure()
        for _, row in latest_holder.iterrows():
            fig_concentration.add_trace(go.Bar(
                name=row["token_symbol"],
                x=["Top 10", "Top 50", "Top 100"],
                y=[row["top_10_pct"], row["top_50_pct"], row["top_100_pct"]],
            ))

        fig_concentration.update_layout(
            title="% of Supply Held by Top Holders",
            yaxis_title="Percentage",
            barmode="group",
        )
        st.plotly_chart(fig_concentration, use_container_width=True)

    with col2:
        # Holder tier distribution
        if len(latest_holder) > 0:
            row = latest_holder.iloc[0]
            tier_data = pd.DataFrame({
                "Tier": ["Whales ($1M+)", "Large ($100K-1M)", "Medium ($10K-100K)", "Small ($1K-10K)", "Micro (<$1K)"],
                "Count": [
                    row.get("whales_1m_plus", 0),
                    row.get("large_100k_1m", 0),
                    row.get("medium_10k_100k", 0),
                    row.get("small_1k_10k", 0),
                    row.get("micro_under_1k", 0),
                ]
            })

            fig_tiers = px.pie(
                tier_data,
                values="Count",
                names="Tier",
                title=f"Holder Distribution by Tier ({latest_holder.iloc[0]['token_symbol']})",
            )
            st.plotly_chart(fig_tiers, use_container_width=True)
else:
    st.info("Holder concentration data not yet available. Run holder snapshot.")

# Recent transfers table
st.subheader("Recent Transfers")

if not recent_transfers.empty:
    st.dataframe(
        recent_transfers.head(20),
        column_config={
            "signature": st.column_config.TextColumn("Signature", width="medium"),
            "block_time": st.column_config.DatetimeColumn("Time", format="YYYY-MM-DD HH:mm"),
            "token_symbol": st.column_config.TextColumn("Token", width="small"),
            "amount_decimal": st.column_config.NumberColumn("Amount", format="$%.2f"),
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("No recent transfers to display.")

# Footer
st.markdown("---")
st.markdown(
    "Built with [Streamlit](https://streamlit.io) | "
    "Data from [Helius](https://helius.xyz) | "
    "Part of the cross-ecosystem stablecoin analytics suite"
)
