"""Helius API client for fetching Solana transactions."""

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import Settings, TARGET_MINTS

logger = structlog.get_logger()


class HeliusClient:
    """Client for Helius Enhanced API."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.base_url = f"https://api.helius.xyz/v0"
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "HeliusClient":
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_signatures_for_address(
        self,
        address: str,
        before: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Fetch transaction signatures for a token mint address."""
        url = f"https://api.helius.xyz/v0/addresses/{address}/transactions"
        params = {
            "api-key": self.settings.helius_api_key,
            "limit": limit,
        }
        if before:
            params["before"] = before

        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_parsed_transactions(self, signatures: list[str]) -> list[dict]:
        """Fetch parsed transactions with enhanced metadata."""
        url = f"{self.base_url}/transactions"
        params = {"api-key": self.settings.helius_api_key}

        response = await self.client.post(
            url,
            params=params,
            json={"transactions": signatures},
        )
        response.raise_for_status()
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_token_accounts(self, mint: str, cursor: str | None = None) -> dict:
        """Fetch all token accounts for a mint using DAS API."""
        url = f"https://api.helius.xyz/v0/token-accounts"
        params = {
            "api-key": self.settings.helius_api_key,
            "mint": mint,
            "limit": 1000,
        }
        if cursor:
            params["cursor"] = cursor

        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def is_stablecoin_transaction(tx: dict) -> bool:
    """Check if transaction involves target stablecoins."""
    # Check token transfers in the parsed transaction
    token_transfers = tx.get("tokenTransfers", [])
    for transfer in token_transfers:
        if transfer.get("mint") in TARGET_MINTS:
            return True

    # Check token balances as fallback
    account_data = tx.get("accountData", [])
    for account in account_data:
        if account.get("tokenBalanceChanges"):
            for change in account["tokenBalanceChanges"]:
                if change.get("mint") in TARGET_MINTS:
                    return True

    return False
