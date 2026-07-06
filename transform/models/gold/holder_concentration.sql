{{
    config(
        materialized='table',
        unique_key=['snapshot_date', 'token_symbol']
    )
}}

-- Holder concentration metrics for moat research
-- Calculates Gini coefficient and top holder percentages

with latest_balances as (
    -- Get the most recent balance for each address
    select
        destination_owner as address,
        token_symbol,
        -- Approximate balance from net transfers (proper version needs account snapshots)
        sum(case
            when destination_owner = address then amount_decimal
            else 0
        end) - sum(case
            when source_owner = address then amount_decimal
            else 0
        end) as balance

    from {{ ref('stablecoin_transfers') }}
    where destination_owner is not null or source_owner is not null
    group by 1, 2
    having balance > 0
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
        holder_count,
        total_supply,

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
    group by token_symbol, holder_count, total_supply
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
