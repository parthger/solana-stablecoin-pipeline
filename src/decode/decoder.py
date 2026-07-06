"""Core instruction decoder for SPL Token operations."""

import struct
from datetime import datetime
from typing import Optional

import structlog
from solders.pubkey import Pubkey

from src.config import (
    TOKEN_PROGRAM,
    TOKEN_2022_PROGRAM,
    TARGET_MINTS,
    TOKEN_METADATA,
    DEX_PROGRAMS,
    BRIDGE_PROGRAMS,
)
from src.decode.models import (
    DecodedEvent,
    TokenTransfer,
    TokenMint,
    TokenBurn,
    EventType,
    TransferContext,
)

logger = structlog.get_logger()


# SPL Token instruction discriminators
class TokenInstruction:
    INITIALIZE_MINT = 0
    INITIALIZE_ACCOUNT = 1
    INITIALIZE_MULTISIG = 2
    TRANSFER = 3
    APPROVE = 4
    REVOKE = 5
    SET_AUTHORITY = 6
    MINT_TO = 7
    BURN = 8
    CLOSE_ACCOUNT = 9
    FREEZE_ACCOUNT = 10
    THAW_ACCOUNT = 11
    TRANSFER_CHECKED = 12
    APPROVE_CHECKED = 13
    MINT_TO_CHECKED = 14
    BURN_CHECKED = 15


class InstructionDecoder:
    """Decodes Solana transactions into structured events."""

    def __init__(self):
        self.token_account_cache: dict[str, dict] = {}

    def decode_transaction(
        self,
        tx: dict,
        token_accounts: Optional[dict[str, dict]] = None,
    ) -> list[DecodedEvent]:
        """
        Decode a transaction into a list of events.

        Args:
            tx: Raw transaction from bronze layer
            token_accounts: Optional mapping of token account -> {mint, owner}

        Returns:
            List of decoded events (transfers, mints, burns)
        """
        if token_accounts:
            self.token_account_cache.update(token_accounts)

        events: list[DecodedEvent] = []
        signature = tx["signature"]
        slot = tx["slot"]
        block_time = tx["block_time"]
        fee_payer = tx["fee_payer"]

        # Build account lookup from Helius pre-parsed data
        self._build_account_cache_from_helius(tx)

        # Process Helius pre-parsed token transfers
        # This is the "easy mode" - Helius does the heavy lifting
        for transfer in tx.get("token_transfers", []):
            event = self._process_helius_transfer(
                transfer=transfer,
                signature=signature,
                slot=slot,
                block_time=block_time,
                fee_payer=fee_payer,
                instructions=tx.get("instructions", []),
            )
            if event:
                events.append(event)

        return events

    def decode_raw_instruction(
        self,
        program_id: str,
        data: bytes,
        accounts: list[str],
        signature: str,
        slot: int,
        block_time: datetime,
        fee_payer: str,
        instruction_index: int,
        inner_index: Optional[int] = None,
        cpi_depth: int = 0,
        parent_program: Optional[str] = None,
    ) -> Optional[DecodedEvent]:
        """
        Decode a raw SPL Token instruction.

        This is the credential - handling raw bytes from the chain.
        """
        if program_id not in (TOKEN_PROGRAM, TOKEN_2022_PROGRAM):
            return None

        if len(data) < 1:
            return None

        discriminator = data[0]

        try:
            if discriminator == TokenInstruction.TRANSFER:
                return self._decode_transfer(
                    data, accounts, signature, slot, block_time, fee_payer,
                    instruction_index, inner_index, cpi_depth, parent_program,
                )
            elif discriminator == TokenInstruction.TRANSFER_CHECKED:
                return self._decode_transfer_checked(
                    data, accounts, signature, slot, block_time, fee_payer,
                    instruction_index, inner_index, cpi_depth, parent_program,
                )
            elif discriminator == TokenInstruction.MINT_TO:
                return self._decode_mint_to(
                    data, accounts, signature, slot, block_time, fee_payer,
                    instruction_index, inner_index, cpi_depth, parent_program,
                )
            elif discriminator == TokenInstruction.MINT_TO_CHECKED:
                return self._decode_mint_to_checked(
                    data, accounts, signature, slot, block_time, fee_payer,
                    instruction_index, inner_index, cpi_depth, parent_program,
                )
            elif discriminator == TokenInstruction.BURN:
                return self._decode_burn(
                    data, accounts, signature, slot, block_time, fee_payer,
                    instruction_index, inner_index, cpi_depth, parent_program,
                )
            elif discriminator == TokenInstruction.BURN_CHECKED:
                return self._decode_burn_checked(
                    data, accounts, signature, slot, block_time, fee_payer,
                    instruction_index, inner_index, cpi_depth, parent_program,
                )
        except Exception as e:
            logger.warning(
                "Failed to decode instruction",
                signature=signature,
                discriminator=discriminator,
                error=str(e),
            )

        return None

    def _decode_transfer(
        self,
        data: bytes,
        accounts: list[str],
        signature: str,
        slot: int,
        block_time: datetime,
        fee_payer: str,
        instruction_index: int,
        inner_index: Optional[int],
        cpi_depth: int,
        parent_program: Optional[str],
    ) -> Optional[TokenTransfer]:
        """Decode Transfer instruction (discriminator 3)."""
        if len(accounts) < 3 or len(data) < 9:
            return None

        source_account = accounts[0]
        destination_account = accounts[1]
        authority = accounts[2]
        amount = struct.unpack("<Q", data[1:9])[0]

        # Look up mint from token account cache
        source_info = self.token_account_cache.get(source_account, {})
        mint = source_info.get("mint")

        if not mint or mint not in TARGET_MINTS:
            return None

        token_info = TOKEN_METADATA[mint]
        dest_info = self.token_account_cache.get(destination_account, {})

        return TokenTransfer(
            signature=signature,
            slot=slot,
            block_time=block_time,
            instruction_index=instruction_index,
            inner_index=inner_index,
            cpi_depth=cpi_depth,
            parent_program=parent_program,
            mint=mint,
            token_symbol=token_info["symbol"],
            amount_raw=amount,
            amount_decimal=amount / (10 ** token_info["decimals"]),
            authority=authority,
            fee_payer=fee_payer,
            source_account=source_account,
            source_owner=source_info.get("owner"),
            destination_account=destination_account,
            destination_owner=dest_info.get("owner"),
            transfer_context=self._classify_context(parent_program),
            dex_program=DEX_PROGRAMS.get(parent_program) if parent_program else None,
        )

    def _decode_transfer_checked(
        self,
        data: bytes,
        accounts: list[str],
        signature: str,
        slot: int,
        block_time: datetime,
        fee_payer: str,
        instruction_index: int,
        inner_index: Optional[int],
        cpi_depth: int,
        parent_program: Optional[str],
    ) -> Optional[TokenTransfer]:
        """Decode TransferChecked instruction (discriminator 12)."""
        if len(accounts) < 4 or len(data) < 10:
            return None

        source_account = accounts[0]
        mint = accounts[1]
        destination_account = accounts[2]
        authority = accounts[3]
        amount = struct.unpack("<Q", data[1:9])[0]

        if mint not in TARGET_MINTS:
            return None

        token_info = TOKEN_METADATA[mint]
        source_info = self.token_account_cache.get(source_account, {})
        dest_info = self.token_account_cache.get(destination_account, {})

        return TokenTransfer(
            signature=signature,
            slot=slot,
            block_time=block_time,
            instruction_index=instruction_index,
            inner_index=inner_index,
            cpi_depth=cpi_depth,
            parent_program=parent_program,
            mint=mint,
            token_symbol=token_info["symbol"],
            amount_raw=amount,
            amount_decimal=amount / (10 ** token_info["decimals"]),
            authority=authority,
            fee_payer=fee_payer,
            source_account=source_account,
            source_owner=source_info.get("owner"),
            destination_account=destination_account,
            destination_owner=dest_info.get("owner"),
            transfer_context=self._classify_context(parent_program),
            dex_program=DEX_PROGRAMS.get(parent_program) if parent_program else None,
        )

    def _decode_mint_to(
        self,
        data: bytes,
        accounts: list[str],
        signature: str,
        slot: int,
        block_time: datetime,
        fee_payer: str,
        instruction_index: int,
        inner_index: Optional[int],
        cpi_depth: int,
        parent_program: Optional[str],
    ) -> Optional[TokenMint]:
        """Decode MintTo instruction (discriminator 7)."""
        if len(accounts) < 3 or len(data) < 9:
            return None

        mint = accounts[0]
        destination_account = accounts[1]
        mint_authority = accounts[2]
        amount = struct.unpack("<Q", data[1:9])[0]

        if mint not in TARGET_MINTS:
            return None

        token_info = TOKEN_METADATA[mint]
        dest_info = self.token_account_cache.get(destination_account, {})

        return TokenMint(
            signature=signature,
            slot=slot,
            block_time=block_time,
            instruction_index=instruction_index,
            inner_index=inner_index,
            cpi_depth=cpi_depth,
            parent_program=parent_program,
            mint=mint,
            token_symbol=token_info["symbol"],
            amount_raw=amount,
            amount_decimal=amount / (10 ** token_info["decimals"]),
            authority=mint_authority,
            fee_payer=fee_payer,
            destination_account=destination_account,
            destination_owner=dest_info.get("owner"),
            mint_authority=mint_authority,
        )

    def _decode_mint_to_checked(
        self,
        data: bytes,
        accounts: list[str],
        signature: str,
        slot: int,
        block_time: datetime,
        fee_payer: str,
        instruction_index: int,
        inner_index: Optional[int],
        cpi_depth: int,
        parent_program: Optional[str],
    ) -> Optional[TokenMint]:
        """Decode MintToChecked instruction (discriminator 14)."""
        # Same accounts layout as MintTo
        return self._decode_mint_to(
            data, accounts, signature, slot, block_time, fee_payer,
            instruction_index, inner_index, cpi_depth, parent_program,
        )

    def _decode_burn(
        self,
        data: bytes,
        accounts: list[str],
        signature: str,
        slot: int,
        block_time: datetime,
        fee_payer: str,
        instruction_index: int,
        inner_index: Optional[int],
        cpi_depth: int,
        parent_program: Optional[str],
    ) -> Optional[TokenBurn]:
        """Decode Burn instruction (discriminator 8)."""
        if len(accounts) < 3 or len(data) < 9:
            return None

        source_account = accounts[0]
        mint = accounts[1]
        burn_authority = accounts[2]
        amount = struct.unpack("<Q", data[1:9])[0]

        if mint not in TARGET_MINTS:
            return None

        token_info = TOKEN_METADATA[mint]
        source_info = self.token_account_cache.get(source_account, {})

        return TokenBurn(
            signature=signature,
            slot=slot,
            block_time=block_time,
            instruction_index=instruction_index,
            inner_index=inner_index,
            cpi_depth=cpi_depth,
            parent_program=parent_program,
            mint=mint,
            token_symbol=token_info["symbol"],
            amount_raw=amount,
            amount_decimal=amount / (10 ** token_info["decimals"]),
            authority=burn_authority,
            fee_payer=fee_payer,
            source_account=source_account,
            source_owner=source_info.get("owner"),
            burn_authority=burn_authority,
        )

    def _decode_burn_checked(
        self,
        data: bytes,
        accounts: list[str],
        signature: str,
        slot: int,
        block_time: datetime,
        fee_payer: str,
        instruction_index: int,
        inner_index: Optional[int],
        cpi_depth: int,
        parent_program: Optional[str],
    ) -> Optional[TokenBurn]:
        """Decode BurnChecked instruction (discriminator 15)."""
        # Same layout as Burn
        return self._decode_burn(
            data, accounts, signature, slot, block_time, fee_payer,
            instruction_index, inner_index, cpi_depth, parent_program,
        )

    def _classify_context(self, parent_program: Optional[str]) -> TransferContext:
        """Classify transfer context based on parent program."""
        if not parent_program:
            return TransferContext.DIRECT

        if parent_program in DEX_PROGRAMS:
            return TransferContext.SWAP

        if parent_program in BRIDGE_PROGRAMS:
            return TransferContext.BRIDGE

        return TransferContext.UNKNOWN

    def _build_account_cache_from_helius(self, tx: dict) -> None:
        """Build token account cache from Helius pre-parsed data."""
        for account in tx.get("account_data", []):
            account_addr = account.get("account")
            if not account_addr:
                continue

            for change in account.get("tokenBalanceChanges", []):
                self.token_account_cache[account_addr] = {
                    "mint": change.get("mint"),
                    "owner": change.get("owner") or account.get("owner"),
                }

    def _process_helius_transfer(
        self,
        transfer: dict,
        signature: str,
        slot: int,
        block_time: datetime,
        fee_payer: str,
        instructions: list[dict],
    ) -> Optional[TokenTransfer]:
        """Process a Helius pre-parsed token transfer."""
        mint = transfer.get("mint")
        if not mint or mint not in TARGET_MINTS:
            return None

        token_info = TOKEN_METADATA[mint]
        amount = transfer.get("tokenAmount", 0)

        # Determine parent program for context classification
        parent_program = None
        if instructions:
            # First non-compute-budget instruction is usually the main program
            for ix in instructions:
                program_id = ix.get("programId")
                if program_id and "ComputeBudget" not in program_id:
                    parent_program = program_id
                    break

        return TokenTransfer(
            signature=signature,
            slot=slot,
            block_time=block_time,
            instruction_index=0,  # Helius doesn't give us precise index
            inner_index=None,
            cpi_depth=0,
            parent_program=parent_program,
            mint=mint,
            token_symbol=token_info["symbol"],
            amount_raw=int(amount * (10 ** token_info["decimals"])),
            amount_decimal=amount,
            authority=transfer.get("fromUserAccount", fee_payer),
            fee_payer=fee_payer,
            source_account=transfer.get("fromTokenAccount", ""),
            source_owner=transfer.get("fromUserAccount"),
            destination_account=transfer.get("toTokenAccount", ""),
            destination_owner=transfer.get("toUserAccount"),
            transfer_context=self._classify_context(parent_program),
            dex_program=DEX_PROGRAMS.get(parent_program) if parent_program else None,
        )
