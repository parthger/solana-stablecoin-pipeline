{{
    config(
        materialized='table',
        unique_key=['snapshot_date', 'token_symbol']
    )
}}

-- Holder concentration metrics for moat research
-- Calculates concentration percentages and holder tier distribution

with inflows as (
    -- Sum incoming transfers per destination
    select
        destination_owner as address,
        token_symbol,
        sum(amount_decimal) as inflow
    from {{ ref('stablecoin_transfers') }}
    where destination_owner is not null
    group by 1, 2
),

outflows as (
    -- Sum outgoing transfers per source
    select
        source_owner as address,
        token_symbol,
        sum(amount_decimal) as outflow
    from {{ ref('stablecoin_transfers') }}
    where source_owner is not null
    group by 1, 2
),

latest_balances as (
    -- Net balance per address
    select
        address,
        token_symbol,
        balance
    from (
        select
            coalesce(i.address, o.address) as address,
            coalesce(i.token_symbol, o.token_symbol) as token_symbol,
            coalesce(i.inflow, 0) - coalesce(o.outflow, 0) as balance
        from inflows i
        full outer join outflows o
            on i.address = o.address and i.token_symbol = o.token_symbol
    ) net_balances
    where balance > 0
),

ranked_holders as (
    select
        token_symbol,
        address,
        balance,
        row_number() over (partition by token_symbol order by balance desc) as rank,
        sum(balance) over (partition by token_symbol) as total_supply,
        count(*) over (partition by token_symbol) as holder_count
    from latest_balances
),

concentration_metrics as (
    select
        token_symbol,
        max(holder_count) as holder_count,
        max(total_supply) as total_supply,

        -- Top holder concentration
        sum(case when rank <= 10 then balance else 0 end) as top_10_balance,
        sum(case when rank <= 50 then balance else 0 end) as top_50_balance,
        sum(case when rank <= 100 then balance else 0 end) as top_100_balance,

        -- Holder tiers
        count(*) filter (where balance >= 1000000) as whales_1m_plus,
        count(*) filter (where balance >= 100000 and balance < 1000000) as large_100k_1m,
        count(*) filter (where balance >= 10000 and balance < 100000) as medium_10k_100k,
        count(*) filter (where balance >= 1000 and balance < 10000) as small_1k_10k,
        count(*) filter (where balance < 1000) as micro_under_1k

    from ranked_holders
    group by token_symbol
)

select
    current_date as snapshot_date,
    token_symbol,
    holder_count,
    total_supply,

    top_10_balance,
    case when total_supply > 0 then top_10_balance / total_supply * 100 else 0 end as top_10_pct,

    top_50_balance,
    case when total_supply > 0 then top_50_balance / total_supply * 100 else 0 end as top_50_pct,

    top_100_balance,
    case when total_supply > 0 then top_100_balance / total_supply * 100 else 0 end as top_100_pct,

    whales_1m_plus,
    large_100k_1m,
    medium_10k_100k,
    small_1k_10k,
    micro_under_1k,

    current_timestamp as updated_at

from concentration_metrics
