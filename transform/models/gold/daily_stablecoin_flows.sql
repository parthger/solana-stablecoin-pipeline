{{
    config(
        materialized='table',
        unique_key=['date', 'token_symbol']
    )
}}

-- Daily aggregated stablecoin flow metrics

with daily_metrics as (
    select
        date_trunc('day', block_time)::date as date,
        token_symbol,

        -- Volume metrics
        count(*) as transfer_count,
        sum(amount_decimal) as transfer_volume,
        count(distinct source_owner) as unique_senders,
        count(distinct destination_owner) as unique_receivers,

        -- Average metrics
        avg(amount_decimal) as avg_transfer_size,
        percentile_cont(0.5) within group (order by amount_decimal) as median_transfer_size,

        -- Large transfer tracking (whale activity)
        count(*) filter (where amount_decimal >= 100000) as large_transfers_100k_plus,
        sum(amount_decimal) filter (where amount_decimal >= 100000) as large_transfer_volume

    from {{ ref('stablecoin_transfers') }}
    group by 1, 2
)

select
    date,
    token_symbol,
    transfer_count,
    transfer_volume,
    unique_senders,
    unique_receivers,
    unique_senders + unique_receivers as unique_addresses,
    avg_transfer_size,
    median_transfer_size,
    large_transfers_100k_plus,
    large_transfer_volume,
    -- Velocity = volume / supply (placeholder - need supply data)
    -- velocity,
    current_timestamp as updated_at

from daily_metrics

order by date desc, token_symbol
