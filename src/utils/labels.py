"""Wallet labeling and classification utilities."""

import json
from pathlib import Path
from typing import Optional

# Known exchange addresses (expand as needed)
KNOWN_LABELS = {
    # CEXs
    "FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiouN5": {"label": "Kraken", "category": "cex"},
    "2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm": {"label": "Coinbase", "category": "cex"},
    "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS": {"label": "Coinbase 2", "category": "cex"},
    "5VCwKtCXgCJ6kit5FybXjvriW3xELsFDhYrPSqtJNmcD": {"label": "Binance", "category": "cex"},
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": {"label": "Binance 2", "category": "cex"},

    # DEXs / Protocols
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": {"label": "Jupiter v6", "category": "dex"},
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": {"label": "Orca Whirlpool", "category": "dex"},
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": {"label": "Raydium AMM", "category": "dex"},

    # Bridges
    "worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth": {"label": "Wormhole", "category": "bridge"},

    # Issuers
    "7q7QyjvMwf9szLMQ6aN1Y8DEF1ot3ueNQHN5G5C9pU2p": {"label": "Circle (USDC)", "category": "issuer"},
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
    Classify a wallet address.

    Returns:
        Dict with 'label', 'category', and 'confidence'
    """
    if labels is None:
        labels = KNOWN_LABELS

    if address in labels:
        return {
            **labels[address],
            "confidence": 1.0,
        }

    # Could add heuristics here (e.g., program-derived addresses)
    return {
        "label": None,
        "category": "unknown",
        "confidence": 0.0,
    }
