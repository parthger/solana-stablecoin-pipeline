{{
    config(
        materialized='table',
        unique_key=['date', 'token_symbol', 'protocol']
    )
}}

-- DEX flow analysis: Volume and activity by protocol
-- Identifies where stablecoin liquidity flows through

with transactions_with_source as (
    select
        t.signature,
        t.source as protocol_raw,
        t.type as tx_type,
        t.block_time,
        t._dlt_id
    from {{ source('bronze', 'transactions') }} t
    where t.success = true
),

transfers_with_protocol as (
    select
        st.signature,
        st.token_symbol,
        st.amount_decimal,
        st.source_owner,
        st.destination_owner,
        st.block_time,
        -- Normalize protocol names
        case
            when t.protocol_raw = 'JUPITER' then 'Jupiter'
            when t.protocol_raw = 'RAYDIUM' then 'Raydium'
            when t.protocol_raw = 'ORCA' then 'Orca'
            when t.protocol_raw = 'METEORA' then 'Meteora'
            when t.protocol_raw = 'METEORA_DAMM_V2' then 'Meteora'
            when t.protocol_raw = 'PUMP_FUN' then 'Pump.fun'
            when t.protocol_raw = 'PUMP_AMM' then 'Pump.fun'
            when t.protocol_raw = 'OKX_DEX_ROUTER' then 'OKX DEX'
            when t.protocol_raw = 'TITAN' then 'Titan'
            when t.protocol_raw = 'DFLOW' then 'DFlow'
            when t.protocol_raw = 'HAWKSIGHT' then 'Hawksight'
            when t.protocol_raw = 'PANCAKESWAP' then 'PancakeSwap'
            when t.protocol_raw = 'KAMINO_LEND' then 'Kamino'
            when t.protocol_raw = 'LIFINITY' then 'Lifinity'
            when t.protocol_raw = 'PHOENIX' then 'Phoenix'
            when t.protocol_raw in ('UNKNOWN', '') or t.protocol_raw is null then 'Unknown'
            else t.protocol_raw
        end as protocol,
        t.tx_type
    from {{ ref('stablecoin_transfers') }} st
    join transactions_with_source t on st.signature = t.signature
),

daily_protocol_flows as (
    select
        cast(block_time as date) as date,
        token_symbol,
        protocol,
        tx_type,
        count(distinct signature) as tx_count,
        count(*) as transfer_count,
        sum(amount_decimal) as volume,
        avg(amount_decimal) as avg_transfer_size,
        max(amount_decimal) as max_transfer,
        count(distinct source_owner) as unique_senders,
        count(distinct destination_owner) as unique_receivers
    from transfers_with_protocol
    group by 1, 2, 3, 4
)

select
    date,
    token_symbol,
    protocol,
    tx_type,
    tx_count,
    transfer_count,
    volume,
    avg_transfer_size,
    max_transfer,
    unique_senders,
    unique_receivers,
    -- Market share calculation (will be computed in a window)
    volume / nullif(sum(volume) over (partition by date, token_symbol), 0) * 100 as volume_share_pct,
    current_timestamp as updated_at

from daily_protocol_flows

order by date desc, volume desc
