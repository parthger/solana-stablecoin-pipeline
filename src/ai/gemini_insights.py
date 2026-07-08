"""AI-powered insights generation using Google Gemini API."""

import os
from typing import Optional
from google import genai
import pandas as pd


def get_gemini_client():
    """Get Gemini client configured with API key."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment")
    return genai.Client(api_key=api_key)


# Default model to use
GEMINI_MODEL = "gemini-2.5-flash"


def generate_daily_summary(
    daily_flows: pd.DataFrame,
    dex_flows: pd.DataFrame,
    wallet_analytics: pd.DataFrame,
) -> str:
    """
    Generate a natural language summary of today's stablecoin activity.

    Args:
        daily_flows: DataFrame with daily transfer metrics
        dex_flows: DataFrame with DEX protocol volumes
        wallet_analytics: DataFrame with wallet classifications

    Returns:
        AI-generated summary string
    """
    client = get_gemini_client()

    # Prepare data context
    context = _prepare_data_context(daily_flows, dex_flows, wallet_analytics)

    prompt = f"""You are a DeFi analyst providing insights on Solana stablecoin activity.

Based on the following data, provide a concise 3-4 paragraph summary covering:
1. Overall volume trends and notable changes
2. Which protocols are seeing the most activity
3. Any interesting whale or bot activity
4. Key takeaways for traders/investors

Be specific with numbers and percentages. Highlight anything unusual.

DATA:
{context}

Provide your analysis:"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )
    return response.text


def detect_anomalies(
    daily_flows: pd.DataFrame,
    lookback_days: int = 7,
) -> list[dict]:
    """
    Use AI to detect anomalies in the data.

    Returns list of detected anomalies with explanations.
    """
    client = get_gemini_client()

    if len(daily_flows) < 2:
        return []

    # Calculate statistics for anomaly detection
    recent = daily_flows.head(lookback_days)
    stats = {
        "avg_volume": recent["transfer_volume"].mean(),
        "std_volume": recent["transfer_volume"].std(),
        "avg_tx_count": recent["transfer_count"].mean(),
        "latest_volume": daily_flows.iloc[0]["transfer_volume"] if len(daily_flows) > 0 else 0,
        "latest_tx_count": daily_flows.iloc[0]["transfer_count"] if len(daily_flows) > 0 else 0,
    }

    # Check for statistical anomalies
    volume_zscore = (stats["latest_volume"] - stats["avg_volume"]) / max(stats["std_volume"], 1)

    prompt = f"""Analyze this stablecoin data for anomalies:

Recent Statistics (last {lookback_days} days):
- Average daily volume: ${stats['avg_volume']:,.2f}
- Standard deviation: ${stats['std_volume']:,.2f}
- Average transaction count: {stats['avg_tx_count']:,.0f}

Today's Data:
- Volume: ${stats['latest_volume']:,.2f}
- Transaction count: {stats['latest_tx_count']:,.0f}
- Volume Z-score: {volume_zscore:.2f}

Full recent data:
{recent.to_string()}

Identify any anomalies. For each anomaly, provide:
1. Type (volume_spike, volume_drop, unusual_activity, whale_movement)
2. Severity (low, medium, high)
3. Brief explanation

Format as JSON array. If no anomalies, return empty array [].
Example: [{{"type": "volume_spike", "severity": "high", "explanation": "Volume 3x above average"}}]

Response (JSON only, no markdown code blocks):"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    import json
    try:
        response_text = response.text.strip()
        # Handle markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])  # Remove first and last lines
        return json.loads(response_text)
    except (json.JSONDecodeError, IndexError):
        return []


def answer_question(
    question: str,
    daily_flows: pd.DataFrame,
    dex_flows: pd.DataFrame,
    wallet_analytics: pd.DataFrame,
) -> str:
    """
    Answer a natural language question about the data.

    Args:
        question: User's question in natural language
        daily_flows: DataFrame with daily transfer metrics
        dex_flows: DataFrame with DEX protocol volumes
        wallet_analytics: DataFrame with wallet classifications

    Returns:
        AI-generated answer string
    """
    client = get_gemini_client()

    context = _prepare_data_context(daily_flows, dex_flows, wallet_analytics)

    prompt = f"""You are a helpful DeFi data analyst. Answer the user's question based on the provided Solana stablecoin data.

DATA:
{context}

USER QUESTION: {question}

Provide a clear, specific answer based on the data. If the data doesn't contain enough information to answer, say so."""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )
    return response.text


def classify_wallet_with_ai(
    wallet: str,
    tx_count: int,
    total_volume: float,
    avg_size: float,
    send_count: int,
    receive_count: int,
    counterparties: list[str],
) -> dict:
    """
    Use AI to classify a wallet with more nuance than rule-based approach.

    Returns classification with confidence and reasoning.
    """
    client = get_gemini_client()

    prompt = f"""Classify this Solana wallet based on its stablecoin activity:

Wallet: {wallet[:20]}...
Transaction Count: {tx_count}
Total Volume: ${total_volume:,.2f}
Average Transfer Size: ${avg_size:,.2f}
Sends: {send_count}, Receives: {receive_count}
Top Counterparties: {counterparties[:5]}

Classify as one of:
- whale: Large holder, big transfers
- market_maker: High frequency, balanced activity
- trader: Active trading patterns
- retail: Small, infrequent activity
- bot: Automated, high frequency, small amounts
- cex: Exchange-like patterns
- protocol: DeFi protocol or smart contract

Respond with JSON only (no markdown):
{{"category": "...", "confidence": 0.0-1.0, "reasoning": "..."}}"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    import json
    try:
        response_text = response.text.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
        return json.loads(response_text)
    except (json.JSONDecodeError, IndexError):
        return {"category": "unknown", "confidence": 0.0, "reasoning": "Failed to classify"}


def generate_alerts(
    daily_flows: pd.DataFrame,
    wallet_analytics: pd.DataFrame,
    thresholds: Optional[dict] = None,
) -> list[dict]:
    """
    Generate smart alerts based on data patterns.

    Returns list of alerts with severity and recommendations.
    """
    if thresholds is None:
        thresholds = {
            "volume_change_pct": 50,
            "whale_threshold": 1_000_000,
            "new_whale_volume": 500_000,
        }

    alerts = []

    if len(daily_flows) >= 2:
        today = daily_flows.iloc[0]["transfer_volume"]
        yesterday = daily_flows.iloc[1]["transfer_volume"]
        change_pct = ((today - yesterday) / max(yesterday, 1)) * 100

        if abs(change_pct) > thresholds["volume_change_pct"]:
            direction = "increased" if change_pct > 0 else "decreased"
            alerts.append({
                "type": "volume_change",
                "severity": "high" if abs(change_pct) > 100 else "medium",
                "title": f"Volume {direction} by {abs(change_pct):.1f}%",
                "description": f"Daily volume went from ${yesterday:,.0f} to ${today:,.0f}",
                "recommendation": "Investigate major transactions for the cause",
            })

    if not wallet_analytics.empty:
        whales = wallet_analytics[wallet_analytics["wallet_category"] == "whale"]
        large_movers = whales[whales["total_volume"] > thresholds["whale_threshold"]]

        if len(large_movers) > 0:
            top_whale = large_movers.iloc[0]
            alerts.append({
                "type": "whale_activity",
                "severity": "medium",
                "title": f"Whale activity detected",
                "description": f"Top whale moved ${top_whale['total_volume']:,.0f}",
                "recommendation": "Monitor for market impact",
            })

    return alerts


def generate_market_prediction(
    daily_flows: pd.DataFrame,
    dex_flows: pd.DataFrame,
) -> dict:
    """
    Generate market predictions based on historical patterns.

    Returns prediction with confidence and reasoning.
    """
    client = get_gemini_client()

    if len(daily_flows) < 3:
        return {"prediction": "Insufficient data", "confidence": 0.0, "reasoning": "Need more historical data"}

    # Calculate trends
    recent = daily_flows.head(7)
    volumes = recent["transfer_volume"].tolist()

    trend = "increasing" if volumes[0] > volumes[-1] else "decreasing" if volumes[0] < volumes[-1] else "stable"
    avg_volume = sum(volumes) / len(volumes)

    prompt = f"""Based on this Solana stablecoin data, provide a short-term market outlook:

Volume Trend (last 7 days): {trend}
Recent Volumes: {[f'${v:,.0f}' for v in volumes[:5]]}
Average Volume: ${avg_volume:,.0f}

Top Protocols by Volume:
{dex_flows.groupby('protocol')['volume'].sum().sort_values(ascending=False).head(5).to_string() if not dex_flows.empty else 'N/A'}

Provide a brief prediction for the next 24-48 hours:
1. Expected volume trend (up/down/stable)
2. Confidence level (0.0-1.0)
3. Key factors to watch
4. Brief reasoning

Format as JSON (no markdown code blocks):
{{"trend": "up/down/stable", "confidence": 0.0-1.0, "factors": ["factor1", "factor2"], "reasoning": "..."}}

Response:"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    import json
    try:
        response_text = response.text.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
        return json.loads(response_text)
    except (json.JSONDecodeError, IndexError):
        return {"trend": "unknown", "confidence": 0.0, "reasoning": "Failed to generate prediction"}


def _prepare_data_context(
    daily_flows: pd.DataFrame,
    dex_flows: pd.DataFrame,
    wallet_analytics: pd.DataFrame,
) -> str:
    """Prepare data context string for AI prompts."""
    context_parts = []

    # Daily flows summary
    if not daily_flows.empty:
        recent = daily_flows.head(7)
        context_parts.append("DAILY FLOWS (last 7 days):")
        context_parts.append(recent[["date", "token_symbol", "transfer_volume", "transfer_count", "unique_senders"]].to_string())

    # DEX flows summary
    if not dex_flows.empty:
        protocol_summary = dex_flows.groupby("protocol").agg({
            "volume": "sum",
            "tx_count": "sum"
        }).sort_values("volume", ascending=False).head(10)
        context_parts.append("\nDEX PROTOCOL VOLUMES:")
        context_parts.append(protocol_summary.to_string())

    # Wallet analytics summary
    if not wallet_analytics.empty:
        category_summary = wallet_analytics.groupby("wallet_category").agg({
            "wallet": "count",
            "total_volume": "sum"
        }).sort_values("total_volume", ascending=False)
        context_parts.append("\nWALLET CATEGORIES:")
        context_parts.append(category_summary.to_string())

        # Top wallets
        top_wallets = wallet_analytics.head(10)[["wallet", "wallet_label", "wallet_category", "total_volume"]]
        context_parts.append("\nTOP 10 WALLETS BY VOLUME:")
        context_parts.append(top_wallets.to_string())

    return "\n".join(context_parts)
