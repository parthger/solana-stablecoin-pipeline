"""Wallet labeling and classification utilities."""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class WalletCategory(str, Enum):
    """Wallet category types."""
    CEX = "cex"
    DEX = "dex"
    BRIDGE = "bridge"
    ISSUER = "issuer"
    PROTOCOL = "protocol"
    MARKET_MAKER = "market_maker"
    WHALE = "whale"
    BOT = "bot"
    RETAIL = "retail"
    UNKNOWN = "unknown"


@dataclass
class WalletLabel:
    """Wallet label with metadata."""
    label: str
    category: WalletCategory
    confidence: float = 1.0
    source: str = "known"  # known, behavior, heuristic


# Known exchange addresses (verified)
KNOWN_LABELS = {
    # === CEXs ===
    "FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiouN5": {"label": "Kraken", "category": "cex"},
    "2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm": {"label": "Coinbase", "category": "cex"},
    "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS": {"label": "Coinbase 2", "category": "cex"},
    "GJRs4FwHtemZ5ZE9x3FNvJ8TMwitKTh21yxdRPqn7npE": {"label": "Coinbase 3", "category": "cex"},
    "5VCwKtCXgCJ6kit5FybXjvriW3xELsFDhYrPSqtJNmcD": {"label": "Binance", "category": "cex"},
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": {"label": "Binance 2", "category": "cex"},
    "3yFwqXBfZY4jBVUafQ1YEXw189y2dN3V5KQq9uzBDy1E": {"label": "OKX", "category": "cex"},
    "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9": {"label": "Bybit", "category": "cex"},
    "ASTyfSima4LLAdDgoFGkgqoKowG1LZFDr9fAQrg7iaJZ": {"label": "FTX (Defunct)", "category": "cex"},
    "CuieVDEDtLo7FypA9SbLM9saXFdb1dsshEkyErMqkRQq": {"label": "Kucoin", "category": "cex"},
    "BmFdpraQhkiDQE6SnfG5omcA1VwzqfXrwtNYBwWTymy6": {"label": "Gate.io", "category": "cex"},

    # === DEXs / Protocols ===
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": {"label": "Jupiter v6", "category": "dex"},
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": {"label": "Jupiter v4", "category": "dex"},
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": {"label": "Orca Whirlpool", "category": "dex"},
    "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP": {"label": "Orca", "category": "dex"},
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": {"label": "Raydium AMM", "category": "dex"},
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": {"label": "Raydium CLMM", "category": "dex"},
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": {"label": "Meteora DLMM", "category": "dex"},
    "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB": {"label": "Meteora", "category": "dex"},
    "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY": {"label": "Phoenix", "category": "dex"},
    "srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX": {"label": "Serum", "category": "dex"},
    "opnb2LAfJYbRMAHHvqjCwQxanZn7ReEHp1k81EohpZb": {"label": "OpenBook", "category": "dex"},
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": {"label": "Pump.fun", "category": "dex"},

    # === Bridges ===
    "worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth": {"label": "Wormhole", "category": "bridge"},
    "wormDTUJ6AWPNvk59vGQbDvGJmqbDTdgWgAqcLBCgUb": {"label": "Wormhole Token Bridge", "category": "bridge"},
    "Portal Bridge": {"label": "Portal (Wormhole)", "category": "bridge"},
    "cctp": {"label": "Circle CCTP", "category": "bridge"},

    # === Issuers / Treasuries ===
    "7q7QyjvMwf9szLMQ6aN1Y8DEF1ot3ueNQHN5G5C9pU2p": {"label": "Circle (USDC)", "category": "issuer"},
    "BJE5MMbqXjVwjAF7oxwPYXnTXDyspzZk4B7sVWXHfyDr": {"label": "Circle Treasury", "category": "issuer"},
    "2wmVCSfPxGPjrnMMn7rchp4uaeoTqN39mXFC2zhPdri9": {"label": "PayPal (PYUSD)", "category": "issuer"},

    # === Lending / DeFi Protocols ===
    "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA": {"label": "Marginfi", "category": "protocol"},
    "KLend2g3cP87ber41NjFMWvHSZtLdEDqv8n8RP4MtJB": {"label": "Kamino Lend", "category": "protocol"},
    "6LtLpnUFNByNXLyCoK9wA2MykKAmQNZKBdY8s47dehDc": {"label": "Kamino", "category": "protocol"},
    "So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo": {"label": "Solend", "category": "protocol"},
    "JD3bq9hGdy38PuWQ4h2YJpELmHVGPPfFSuFkpzAd9zfu": {"label": "Mango Markets", "category": "protocol"},
    "DjVE6JNiYqPL2QXyCUUh8rNjHrbz9hXHNYt99MQ59qw1": {"label": "Drift", "category": "protocol"},

    # === Market Makers ===
    "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1": {"label": "Wintermute", "category": "market_maker"},
    "HWHvQhFmJB6gPtqJx3gjxHX1iDZhQ9WJorxwb3iTWVHi": {"label": "Jump Trading", "category": "market_maker"},
    "rndshKFf48HhGaPbaCd3WQYtgCNKzRgVQ3U2we4Cvf9": {"label": "Alameda (Defunct)", "category": "market_maker"},

    # === Staking / Liquid Staking ===
    "marinade": {"label": "Marinade Finance", "category": "protocol"},
    "SPoo1Ku8WFXoNDMHPsrGSTSG1Y47rzgn41SLUNakuHy": {"label": "Marinade Staking", "category": "protocol"},
    "jito": {"label": "Jito", "category": "protocol"},
}


# Behavior thresholds for auto-classification
BEHAVIOR_THRESHOLDS = {
    "whale_min_transfer": 100_000,  # $100K+ single transfer
    "whale_min_volume": 1_000_000,  # $1M+ total volume
    "bot_min_tx_count": 50,  # 50+ transactions
    "bot_max_avg_size": 1_000,  # Under $1K avg
    "market_maker_min_tx": 100,  # High frequency
    "market_maker_balanced_ratio": 0.3,  # Send/receive ratio near 1
    "retail_max_tx": 10,  # Low transaction count
    "retail_max_volume": 10_000,  # Under $10K total
}


def load_wallet_labels(custom_labels_path: Optional[Path] = None) -> dict[str, dict]:
    """Load wallet labels from default + custom sources."""
    labels = KNOWN_LABELS.copy()

    if custom_labels_path and custom_labels_path.exists():
        with open(custom_labels_path) as f:
            custom = json.load(f)
            labels.update(custom)

    return labels


def classify_wallet(
    address: str,
    labels: Optional[dict[str, dict]] = None,
) -> dict:
    """
    Classify a wallet address using known labels.

    Returns:
        Dict with 'label', 'category', and 'confidence'
    """
    if labels is None:
        labels = KNOWN_LABELS

    if address in labels:
        return {
            **labels[address],
            "confidence": 1.0,
            "source": "known",
        }

    return {
        "label": None,
        "category": "unknown",
        "confidence": 0.0,
        "source": None,
    }


def classify_by_behavior(
    address: str,
    tx_count: int,
    total_volume: float,
    avg_size: float,
    max_transfer: float,
    send_count: int = 0,
    receive_count: int = 0,
    labels: Optional[dict[str, dict]] = None,
) -> dict:
    """
    Classify a wallet based on transaction behavior.

    Args:
        address: Wallet address
        tx_count: Total transaction count
        total_volume: Total USD volume
        avg_size: Average transfer size
        max_transfer: Maximum single transfer
        send_count: Number of sends
        receive_count: Number of receives
        labels: Optional known labels dict

    Returns:
        Dict with classification info
    """
    # First check known labels
    if labels is None:
        labels = KNOWN_LABELS

    if address in labels:
        return {
            **labels[address],
            "confidence": 1.0,
            "source": "known",
        }

    thresholds = BEHAVIOR_THRESHOLDS

    # Whale detection
    if max_transfer >= thresholds["whale_min_transfer"] or total_volume >= thresholds["whale_min_volume"]:
        return {
            "label": "Whale",
            "category": "whale",
            "confidence": 0.8,
            "source": "behavior",
        }

    # Bot detection (high frequency, small amounts)
    if tx_count >= thresholds["bot_min_tx_count"] and avg_size <= thresholds["bot_max_avg_size"]:
        return {
            "label": "Bot/MEV",
            "category": "bot",
            "confidence": 0.7,
            "source": "behavior",
        }

    # Market maker detection (high frequency, balanced sends/receives)
    if tx_count >= thresholds["market_maker_min_tx"]:
        total = send_count + receive_count
        if total > 0:
            ratio = min(send_count, receive_count) / max(send_count, receive_count) if max(send_count, receive_count) > 0 else 0
            if ratio >= thresholds["market_maker_balanced_ratio"]:
                return {
                    "label": "Market Maker",
                    "category": "market_maker",
                    "confidence": 0.6,
                    "source": "behavior",
                }

    # Retail detection (low activity)
    if tx_count <= thresholds["retail_max_tx"] and total_volume <= thresholds["retail_max_volume"]:
        return {
            "label": "Retail",
            "category": "retail",
            "confidence": 0.5,
            "source": "behavior",
        }

    # Default: Trader (active but not classified)
    if tx_count > thresholds["retail_max_tx"]:
        return {
            "label": "Trader",
            "category": "unknown",
            "confidence": 0.4,
            "source": "behavior",
        }

    return {
        "label": None,
        "category": "unknown",
        "confidence": 0.0,
        "source": None,
    }


def get_category_color(category: str) -> str:
    """Get display color for category."""
    colors = {
        "cex": "#FF6B6B",
        "dex": "#4ECDC4",
        "bridge": "#45B7D1",
        "issuer": "#96CEB4",
        "protocol": "#FFEAA7",
        "market_maker": "#DDA0DD",
        "whale": "#FF8C00",
        "bot": "#808080",
        "retail": "#98D8C8",
        "unknown": "#CCCCCC",
    }
    return colors.get(category, "#CCCCCC")


def get_all_known_addresses() -> list[str]:
    """Get list of all known labeled addresses."""
    return list(KNOWN_LABELS.keys())


def get_addresses_by_category(category: str) -> list[tuple[str, str]]:
    """Get all addresses for a given category."""
    return [
        (addr, info["label"])
        for addr, info in KNOWN_LABELS.items()
        if info.get("category") == category
    ]
