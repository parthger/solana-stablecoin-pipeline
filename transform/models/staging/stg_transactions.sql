{{
    config(
        materialized='view'
    )
}}

-- Staging view over bronze transactions
-- Filters to successful stablecoin transactions only

select
    signature,
    slot,
    block_time,
    fee,
    fee_payer,
    success,
    source,
    type,
    description,
    token_transfers,
    native_transfers,
    account_data,
    instructions,
    source_mint,
    ingested_at

from {{ source('bronze', 'transactions') }}

where success = true
