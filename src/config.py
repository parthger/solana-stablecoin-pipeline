"""Pipeline configuration and constants."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Pipeline settings loaded from environment."""

    helius_api_key: str
    database_url: str = "duckdb:///data/pipeline.duckdb"

    # Optional streaming config
    yellowstone_endpoint: str | None = None
    yellowstone_token: str | None = None

    # Ingestion settings
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Target stablecoin mints
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
PYUSD_MINT = "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo"
TARGET_MINTS = {USDC_MINT, PYUSD_MINT}

# Program IDs
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
ASSOCIATED_TOKEN_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
VOTE_PROGRAM = "Vote111111111111111111111111111111111111111"

# Known DEX programs for classification
DEX_PROGRAMS = {
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "jupiter",
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": "jupiter_v4",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "orca_whirlpool",
    "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP": "orca_v2",
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": "raydium_clmm",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "raydium_amm",
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": "meteora_dlmm",
}

# Known bridge programs
BRIDGE_PROGRAMS = {
    "worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth": "wormhole",
    "Portal Bridge": "wormhole_token_bridge",
}

# Token metadata
TOKEN_METADATA = {
    USDC_MINT: {"symbol": "USDC", "decimals": 6},
    PYUSD_MINT: {"symbol": "PYUSD", "decimals": 6},
}
