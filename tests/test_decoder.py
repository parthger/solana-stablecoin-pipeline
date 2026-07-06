"""Tests for instruction decoder."""

import struct
from datetime import datetime, timezone

import pytest

from src.decode.decoder import InstructionDecoder, TokenInstruction
from src.decode.models import TokenTransfer, TokenMint, TokenBurn, TransferContext
from src.config import USDC_MINT, TOKEN_PROGRAM


@pytest.fixture
def decoder():
    """Create decoder instance with test token accounts."""
    d = InstructionDecoder()
    # Pre-populate cache with test accounts
    d.token_account_cache = {
        "SourceTokenAccount111111111111111111111111111": {
            "mint": USDC_MINT,
            "owner": "SourceOwner11111111111111111111111111111111",
        },
        "DestTokenAccount1111111111111111111111111111": {
            "mint": USDC_MINT,
            "owner": "DestOwner111111111111111111111111111111111",
        },
    }
    return d


@pytest.fixture
def base_params():
    """Common parameters for instruction decoding."""
    return {
        "signature": "test_signature_123",
        "slot": 123456789,
        "block_time": datetime.now(timezone.utc),
        "fee_payer": "FeePayer111111111111111111111111111111111",
        "instruction_index": 0,
        "inner_index": None,
        "cpi_depth": 0,
        "parent_program": None,
    }


class TestTransferDecoding:
    """Test Transfer instruction decoding."""

    def test_decode_transfer_basic(self, decoder, base_params):
        """Test basic transfer decoding."""
        # Build Transfer instruction data
        # Discriminator (1 byte) + amount (8 bytes little-endian)
        amount = 1_000_000  # 1 USDC
        data = bytes([TokenInstruction.TRANSFER]) + struct.pack("<Q", amount)

        accounts = [
            "SourceTokenAccount111111111111111111111111111",
            "DestTokenAccount1111111111111111111111111111",
            "Authority1111111111111111111111111111111111",
        ]

        result = decoder.decode_raw_instruction(
            program_id=TOKEN_PROGRAM,
            data=data,
            accounts=accounts,
            **base_params,
        )

        assert result is not None
        assert isinstance(result, TokenTransfer)
        assert result.amount_raw == 1_000_000
        assert result.amount_decimal == 1.0
        assert result.token_symbol == "USDC"
        assert result.source_owner == "SourceOwner11111111111111111111111111111111"
        assert result.destination_owner == "DestOwner111111111111111111111111111111111"
        assert result.transfer_context == TransferContext.DIRECT

    def test_decode_transfer_with_dex_parent(self, decoder, base_params):
        """Test transfer inside a DEX swap is classified correctly."""
        amount = 5_000_000_000  # 5000 USDC
        data = bytes([TokenInstruction.TRANSFER]) + struct.pack("<Q", amount)

        accounts = [
            "SourceTokenAccount111111111111111111111111111",
            "DestTokenAccount1111111111111111111111111111",
            "Authority1111111111111111111111111111111111",
        ]

        base_params["parent_program"] = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
        base_params["cpi_depth"] = 1

        result = decoder.decode_raw_instruction(
            program_id=TOKEN_PROGRAM,
            data=data,
            accounts=accounts,
            **base_params,
        )

        assert result is not None
        assert result.transfer_context == TransferContext.SWAP
        assert result.dex_program == "jupiter"

    def test_decode_transfer_insufficient_accounts(self, decoder, base_params):
        """Test that insufficient accounts returns None."""
        data = bytes([TokenInstruction.TRANSFER]) + struct.pack("<Q", 1000)
        accounts = ["OnlyOneAccount"]  # Need 3

        result = decoder.decode_raw_instruction(
            program_id=TOKEN_PROGRAM,
            data=data,
            accounts=accounts,
            **base_params,
        )

        assert result is None


class TestMintDecoding:
    """Test MintTo instruction decoding."""

    def test_decode_mint_to(self, decoder, base_params):
        """Test MintTo decoding."""
        amount = 10_000_000_000  # 10,000 USDC
        data = bytes([TokenInstruction.MINT_TO]) + struct.pack("<Q", amount)

        accounts = [
            USDC_MINT,  # Mint account
            "DestTokenAccount1111111111111111111111111111",
            "MintAuthority11111111111111111111111111111",
        ]

        result = decoder.decode_raw_instruction(
            program_id=TOKEN_PROGRAM,
            data=data,
            accounts=accounts,
            **base_params,
        )

        assert result is not None
        assert isinstance(result, TokenMint)
        assert result.amount_raw == 10_000_000_000
        assert result.amount_decimal == 10_000.0
        assert result.mint_authority == "MintAuthority11111111111111111111111111111"


class TestBurnDecoding:
    """Test Burn instruction decoding."""

    def test_decode_burn(self, decoder, base_params):
        """Test Burn decoding."""
        amount = 500_000_000  # 500 USDC
        data = bytes([TokenInstruction.BURN]) + struct.pack("<Q", amount)

        accounts = [
            "SourceTokenAccount111111111111111111111111111",
            USDC_MINT,
            "BurnAuthority111111111111111111111111111111",
        ]

        result = decoder.decode_raw_instruction(
            program_id=TOKEN_PROGRAM,
            data=data,
            accounts=accounts,
            **base_params,
        )

        assert result is not None
        assert isinstance(result, TokenBurn)
        assert result.amount_raw == 500_000_000
        assert result.amount_decimal == 500.0
        assert result.burn_authority == "BurnAuthority111111111111111111111111111111"


class TestNonTargetMint:
    """Test that non-target mints are ignored."""

    def test_ignores_non_target_mint(self, decoder, base_params):
        """Test that non-USDC/PYUSD mints return None."""
        decoder.token_account_cache["RandomAccount"] = {
            "mint": "SomeOtherMint11111111111111111111111111111",
            "owner": "Owner",
        }

        data = bytes([TokenInstruction.TRANSFER]) + struct.pack("<Q", 1000)
        accounts = ["RandomAccount", "RandomAccount2", "Authority"]

        result = decoder.decode_raw_instruction(
            program_id=TOKEN_PROGRAM,
            data=data,
            accounts=accounts,
            **base_params,
        )

        assert result is None
