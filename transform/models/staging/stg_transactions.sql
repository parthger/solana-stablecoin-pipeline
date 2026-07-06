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
    source_mint,
    ingested_at,
    _dlt_id

from {{ source('bronze', 'transactions') }}

where success = true
