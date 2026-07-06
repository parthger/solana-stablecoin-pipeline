{{
    config(
        materialized='table',
        unique_key='transfer_id'
    )
}}

-- Join transactions with token transfers (dlt normalized structure)
-- This is the silver layer: decoded, typed, enriched

with token_transfers as (
    select
        from_token_account,
        to_token_account,
        from_user_account,
        to_user_account,
        token_amount,
        mint,
        _dlt_root_id,
        _dlt_list_idx
    from {{ source('bronze', 'transactions__token_transfers') }}
),

transactions as (
    select
        signature,
        slot,
        block_time,
        fee_payer,
        _dlt_id
    from {{ ref('stg_transactions') }}
),

joined_transfers as (
    select
        -- Generate unique ID
        md5(t.signature || '-' || coalesce(tt.from_token_account, '') || '-' || coalesce(tt.to_token_account, '') || '-' || cast(coalesce(tt.token_amount, 0) as varchar) || '-' || cast(tt._dlt_list_idx as varchar)) as transfer_id,

        t.signature,
        t.slot,
        t.block_time,

        -- Token details
        tt.mint,
        case
            when tt.mint = '{{ var("usdc_mint") }}' then 'USDC'
            when tt.mint = '{{ var("pyusd_mint") }}' then 'PYUSD'
            else 'OTHER'
        end as token_symbol,

        -- Accounts
        tt.from_token_account as source_account,
        tt.from_user_account as source_owner,
        tt.to_token_account as destination_account,
        tt.to_user_account as destination_owner,

        -- Amount
        tt.token_amount as amount_decimal,
        cast(tt.token_amount * 1000000 as bigint) as amount_raw,

        t.fee_payer

    from token_transfers tt
    inner join transactions t on tt._dlt_root_id = t._dlt_id
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

from joined_transfers

where mint in ('{{ var("usdc_mint") }}', '{{ var("pyusd_mint") }}')
  and amount_decimal > 0
