"""Data models for decoded events."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class EventType(str, Enum):
    TRANSFER = "transfer"
    MINT = "mint"
    BURN = "burn"
    UNKNOWN = "unknown"


class TransferContext(str, Enum):
    DIRECT = "direct"
    SWAP = "swap"
    BRIDGE = "bridge"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    UNKNOWN = "unknown"


class DecodedEvent(BaseModel):
    """Base class for decoded events."""

    signature: str
    slot: int
    block_time: datetime
    event_type: EventType

    # Instruction position
    instruction_index: int
    inner_index: Optional[int] = None
    cpi_depth: int = 0
    parent_program: Optional[str] = None

    # Common fields
    mint: str
    token_symbol: str
    amount_raw: int
    amount_decimal: float

    authority: str
    fee_payer: str


class TokenTransfer(DecodedEvent):
    """Decoded SPL Token transfer event."""

    event_type: EventType = EventType.TRANSFER

    source_account: str
    source_owner: Optional[str] = None
    destination_account: str
    destination_owner: Optional[str] = None

    # Classification
    transfer_context: TransferContext = TransferContext.UNKNOWN
    dex_program: Optional[str] = None


class TokenMint(DecodedEvent):
    """Decoded SPL Token mint event."""

    event_type: EventType = EventType.MINT

    destination_account: str
    destination_owner: Optional[str] = None
    mint_authority: str


class TokenBurn(DecodedEvent):
    """Decoded SPL Token burn event."""

    event_type: EventType = EventType.BURN

    source_account: str
    source_owner: Optional[str] = None
    burn_authority: str
