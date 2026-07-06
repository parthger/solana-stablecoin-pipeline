{{
    config(
        materialized='table',
        unique_key='transfer_id'
    )
}}

-- Flatten token transfers from staged transactions
-- This is the silver layer: decoded, typed, enriched

with transfers_unnested as (
    select
        signature,
        slot,
        block_time,
        fee_payer,
        -- Unnest the token_transfers JSON array
        unnest(token_transfers) as transfer
    from {{ ref('stg_transactions') }}
    where token_transfers is not null
      and json_array_length(token_transfers) > 0
),

parsed_transfers as (
    select
        -- Generate unique ID
        md5(signature || '-' || coalesce(transfer->>'fromTokenAccount', '') || '-' || coalesce(transfer->>'toTokenAccount', '') || '-' || coalesce(transfer->>'tokenAmount', '0')) as transfer_id,

        signature,
        slot,
        block_time,

        -- Token details
        transfer->>'mint' as mint,
        case
            when transfer->>'mint' = '{{ var("usdc_mint") }}' then 'USDC'
            when transfer->>'mint' = '{{ var("pyusd_mint") }}' then 'PYUSD'
            else 'OTHER'
        end as token_symbol,

        -- Accounts
        transfer->>'fromTokenAccount' as source_account,
        transfer->>'fromUserAccount' as source_owner,
        transfer->>'toTokenAccount' as destination_account,
        transfer->>'toUserAccount' as destination_owner,

        -- Amount
        cast(transfer->>'tokenAmount' as decimal(38, 18)) as amount_decimal,
        cast(cast(transfer->>'tokenAmount' as decimal(38, 18)) * 1000000 as bigint) as amount_raw,

        fee_payer

    from transfers_unnested
)

select
    transfer_id,
    signature,
    slot,
    block_time,
    mint,
    token_symbol,
    source_account,
    source_owner,
    destination_account,
    destination_owner,
    amount_raw,
    amount_decimal,
    fee_payer,
    current_timestamp as processed_at

from parsed_transfers

where mint in ('{{ var("usdc_mint") }}', '{{ var("pyusd_mint") }}')
  and amount_decimal > 0
