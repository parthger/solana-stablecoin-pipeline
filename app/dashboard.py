"""Streamlit dashboard for Solana stablecoin analytics."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb
from pathlib import Path
import os
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Check if AI features are available
AI_AVAILABLE = bool(os.getenv("ANTHROPIC_API_KEY"))

# Page config
st.set_page_config(
    page_title="Solana Stablecoin Flows",
    page_icon="💵",
    layout="wide",
)

# Database connection
DB_PATH = Path(__file__).parent.parent / "solana_stablecoins.duckdb"


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


def load_dex_flows() -> pd.DataFrame:
    """Load DEX flow metrics."""
    conn = get_connection()
    query = """
        SELECT
            protocol,
            token_symbol,
            sum(volume) as volume,
            sum(tx_count) as tx_count,
            avg(volume_share_pct) as volume_share_pct,
            max(max_transfer) as max_transfer
        FROM gold.dex_flows
        GROUP BY protocol, token_symbol
        ORDER BY volume DESC
    """
    try:
        return conn.execute(query).fetchdf()
    except Exception:
        return pd.DataFrame()


def load_wallet_analytics() -> pd.DataFrame:
    """Load wallet classification data."""
    conn = get_connection()
    query = """
        SELECT
            wallet,
            token_symbol,
            wallet_label,
            wallet_category,
            confidence,
            classification_source,
            total_tx_count,
            total_volume,
            net_flow,
            max_transfer
        FROM gold.wallet_analytics
        ORDER BY total_volume DESC
    """
    try:
        return conn.execute(query).fetchdf()
    except Exception:
        return pd.DataFrame()


def load_wallet_category_summary() -> pd.DataFrame:
    """Load wallet category summary."""
    conn = get_connection()
    query = """
        SELECT
            wallet_category,
            count(distinct wallet) as wallet_count,
            sum(total_volume) as total_volume,
            sum(total_tx_count) as total_txs,
            avg(total_volume) as avg_volume
        FROM gold.wallet_analytics
        GROUP BY wallet_category
        ORDER BY total_volume DESC
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

# AI Features toggle
st.sidebar.header("AI Features")
if AI_AVAILABLE:
    enable_ai = st.sidebar.checkbox("Enable AI Insights", value=True)
    if enable_ai:
        st.sidebar.success("Claude AI enabled")
else:
    st.sidebar.warning("Set ANTHROPIC_API_KEY to enable AI features")
    enable_ai = False

# Load data
daily_flows = load_daily_flows()
holder_data = load_holder_concentration()
dex_flows = load_dex_flows()
wallet_analytics = load_wallet_analytics()
wallet_categories = load_wallet_category_summary()
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
    if not dex_flows.empty:
        dex_flows = dex_flows[dex_flows["token_symbol"].isin(token_filter)]
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

# AI Insights Section
if enable_ai and AI_AVAILABLE:
    st.subheader("🤖 AI-Powered Insights")

    ai_tab1, ai_tab2, ai_tab3 = st.tabs(["Daily Summary", "Anomaly Detection", "Ask AI"])

    with ai_tab1:
        if st.button("Generate Daily Summary", key="gen_summary"):
            with st.spinner("Claude is analyzing the data..."):
                try:
                    from src.ai.insights import generate_daily_summary
                    summary = generate_daily_summary(daily_flows, dex_flows, wallet_analytics)
                    st.markdown(summary)
                except Exception as e:
                    st.error(f"Error generating summary: {e}")
        else:
            st.info("Click the button to generate an AI summary of today's stablecoin activity.")

    with ai_tab2:
        if st.button("Detect Anomalies", key="detect_anomalies"):
            with st.spinner("Scanning for anomalies..."):
                try:
                    from src.ai.insights import detect_anomalies, generate_alerts
                    anomalies = detect_anomalies(daily_flows)
                    alerts = generate_alerts(daily_flows, wallet_analytics)

                    if anomalies:
                        st.warning(f"Found {len(anomalies)} anomalies")
                        for a in anomalies:
                            severity_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(a.get("severity", "low"), "⚪")
                            st.markdown(f"{severity_color} **{a.get('type', 'Unknown')}**: {a.get('explanation', 'No details')}")
                    else:
                        st.success("No anomalies detected")

                    if alerts:
                        st.markdown("---")
                        st.markdown("**Smart Alerts:**")
                        for alert in alerts:
                            severity_icon = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}.get(alert.get("severity", "low"), "📌")
                            with st.expander(f"{severity_icon} {alert.get('title', 'Alert')}"):
                                st.write(alert.get("description", ""))
                                st.caption(f"Recommendation: {alert.get('recommendation', 'N/A')}")
                except Exception as e:
                    st.error(f"Error detecting anomalies: {e}")
        else:
            st.info("Click to scan for unusual patterns in the data.")

    with ai_tab3:
        user_question = st.text_input(
            "Ask a question about the data:",
            placeholder="e.g., Which protocol has the highest volume today?"
        )
        if user_question:
            with st.spinner("Thinking..."):
                try:
                    from src.ai.insights import answer_question
                    answer = answer_question(user_question, daily_flows, dex_flows, wallet_analytics)
                    st.markdown(answer)
                except Exception as e:
                    st.error(f"Error answering question: {e}")

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

# DEX Flow Analysis (NEW SECTION)
st.subheader("🔄 DEX & Protocol Flow Analysis")

if not dex_flows.empty:
    col1, col2 = st.columns(2)

    with col1:
        # Volume by protocol
        protocol_totals = dex_flows.groupby("protocol").agg({
            "volume": "sum",
            "tx_count": "sum"
        }).reset_index().sort_values("volume", ascending=False).head(10)

        fig_protocol = px.bar(
            protocol_totals,
            x="protocol",
            y="volume",
            title="Volume by Protocol (Top 10)",
            labels={"volume": "Volume (USD)", "protocol": "Protocol"},
            color="volume",
            color_continuous_scale="Viridis",
        )
        fig_protocol.update_layout(showlegend=False)
        st.plotly_chart(fig_protocol, use_container_width=True)

    with col2:
        # Protocol market share
        fig_pie = px.pie(
            protocol_totals.head(8),
            values="volume",
            names="protocol",
            title="Protocol Market Share",
            hole=0.4,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Protocol breakdown table
    st.markdown("**Protocol Details**")
    display_dex = dex_flows.copy()
    display_dex["volume"] = display_dex["volume"].apply(lambda x: f"${x:,.2f}")
    display_dex["max_transfer"] = display_dex["max_transfer"].apply(lambda x: f"${x:,.2f}")
    display_dex["volume_share_pct"] = display_dex["volume_share_pct"].apply(lambda x: f"{x:.2f}%")

    st.dataframe(
        display_dex[["protocol", "token_symbol", "volume", "tx_count", "volume_share_pct", "max_transfer"]].head(15),
        column_config={
            "protocol": st.column_config.TextColumn("Protocol", width="medium"),
            "token_symbol": st.column_config.TextColumn("Token", width="small"),
            "volume": st.column_config.TextColumn("Volume", width="medium"),
            "tx_count": st.column_config.NumberColumn("Transactions", format="%d"),
            "volume_share_pct": st.column_config.TextColumn("Share %", width="small"),
            "max_transfer": st.column_config.TextColumn("Max Transfer", width="medium"),
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("DEX flow data not available. Run `dbt run --select dex_flows` to generate.")

# Wallet Analytics Section
st.subheader("👛 Wallet Classification & Analytics")

if not wallet_categories.empty:
    col1, col2 = st.columns(2)

    with col1:
        # Volume by wallet category
        fig_cat_vol = px.bar(
            wallet_categories,
            x="wallet_category",
            y="total_volume",
            title="Volume by Wallet Category",
            labels={"total_volume": "Volume (USD)", "wallet_category": "Category"},
            color="wallet_category",
            color_discrete_map={
                "whale": "#FF8C00",
                "bot": "#808080",
                "trader": "#4ECDC4",
                "retail": "#98D8C8",
                "market_maker": "#DDA0DD",
                "cex": "#FF6B6B",
                "unknown": "#CCCCCC",
            }
        )
        fig_cat_vol.update_layout(showlegend=False)
        st.plotly_chart(fig_cat_vol, use_container_width=True)

    with col2:
        # Wallet count by category
        fig_cat_count = px.pie(
            wallet_categories,
            values="wallet_count",
            names="wallet_category",
            title="Wallet Distribution by Category",
            hole=0.4,
            color="wallet_category",
            color_discrete_map={
                "whale": "#FF8C00",
                "bot": "#808080",
                "trader": "#4ECDC4",
                "retail": "#98D8C8",
                "market_maker": "#DDA0DD",
                "cex": "#FF6B6B",
                "unknown": "#CCCCCC",
            }
        )
        st.plotly_chart(fig_cat_count, use_container_width=True)

    # Top wallets table
    st.markdown("**Top Wallets by Volume**")
    if not wallet_analytics.empty:
        display_wallets = wallet_analytics.head(15).copy()
        display_wallets["wallet_short"] = display_wallets["wallet"].apply(lambda x: x[:12] + "..." if len(x) > 12 else x)
        display_wallets["total_volume_fmt"] = display_wallets["total_volume"].apply(lambda x: f"${x:,.2f}")
        display_wallets["net_flow_fmt"] = display_wallets["net_flow"].apply(lambda x: f"${x:+,.2f}")

        st.dataframe(
            display_wallets[["wallet_short", "token_symbol", "wallet_label", "wallet_category", "total_volume_fmt", "total_tx_count", "net_flow_fmt"]],
            column_config={
                "wallet_short": st.column_config.TextColumn("Wallet", width="medium"),
                "token_symbol": st.column_config.TextColumn("Token", width="small"),
                "wallet_label": st.column_config.TextColumn("Label", width="small"),
                "wallet_category": st.column_config.TextColumn("Category", width="small"),
                "total_volume_fmt": st.column_config.TextColumn("Volume", width="medium"),
                "total_tx_count": st.column_config.NumberColumn("Txs", format="%d"),
                "net_flow_fmt": st.column_config.TextColumn("Net Flow", width="medium"),
            },
            hide_index=True,
            use_container_width=True,
        )

    # Category stats
    st.markdown("**Category Summary**")
    cat_display = wallet_categories.copy()
    cat_display["total_volume"] = cat_display["total_volume"].apply(lambda x: f"${x:,.2f}")
    cat_display["avg_volume"] = cat_display["avg_volume"].apply(lambda x: f"${x:,.2f}")

    st.dataframe(
        cat_display,
        column_config={
            "wallet_category": st.column_config.TextColumn("Category", width="medium"),
            "wallet_count": st.column_config.NumberColumn("Wallets", format="%d"),
            "total_volume": st.column_config.TextColumn("Total Volume", width="medium"),
            "total_txs": st.column_config.NumberColumn("Total Txs", format="%d"),
            "avg_volume": st.column_config.TextColumn("Avg Volume", width="medium"),
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("Wallet analytics not available. Run `dbt run --select wallet_analytics` to generate.")

# Holder concentration (for moat research)
st.subheader("🏛️ Holder Concentration (Moat Metrics)")

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
st.subheader("📋 Recent Transfers")

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
