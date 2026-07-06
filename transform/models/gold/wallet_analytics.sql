{{
    config(
        materialized='table',
        unique_key='wallet'
    )
}}

-- Wallet analytics with behavioral classification
-- Identifies whales, bots, market makers, and retail users

with send_activity as (
    select
        source_owner as wallet,
        token_symbol,
        count(*) as send_count,
        sum(amount_decimal) as send_volume,
        avg(amount_decimal) as avg_send_size,
        max(amount_decimal) as max_send
    from {{ ref('stablecoin_transfers') }}
    where source_owner is not null
    group by 1, 2
),

receive_activity as (
    select
        destination_owner as wallet,
        token_symbol,
        count(*) as receive_count,
        sum(amount_decimal) as receive_volume,
        avg(amount_decimal) as avg_receive_size,
        max(amount_decimal) as max_receive
    from {{ ref('stablecoin_transfers') }}
    where destination_owner is not null
    group by 1, 2
),

wallet_stats as (
    select
        coalesce(s.wallet, r.wallet) as wallet,
        coalesce(s.token_symbol, r.token_symbol) as token_symbol,
        coalesce(s.send_count, 0) as send_count,
        coalesce(r.receive_count, 0) as receive_count,
        coalesce(s.send_count, 0) + coalesce(r.receive_count, 0) as total_tx_count,
        coalesce(s.send_volume, 0) as send_volume,
        coalesce(r.receive_volume, 0) as receive_volume,
        coalesce(s.send_volume, 0) + coalesce(r.receive_volume, 0) as total_volume,
        coalesce(r.receive_volume, 0) - coalesce(s.send_volume, 0) as net_flow,
        (coalesce(s.avg_send_size, 0) + coalesce(r.avg_receive_size, 0)) /
            nullif(case when s.wallet is not null and r.wallet is not null then 2
                        when s.wallet is not null or r.wallet is not null then 1
                        else 1 end, 0) as avg_transfer_size,
        greatest(coalesce(s.max_send, 0), coalesce(r.max_receive, 0)) as max_transfer
    from send_activity s
    full outer join receive_activity r
        on s.wallet = r.wallet and s.token_symbol = r.token_symbol
),

-- Known wallet labels (manually curated)
known_wallets as (
    select * from (values
        -- CEXs
        ('FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiouN5', 'Kraken', 'cex'),
        ('2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm', 'Coinbase', 'cex'),
        ('H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS', 'Coinbase 2', 'cex'),
        ('5VCwKtCXgCJ6kit5FybXjvriW3xELsFDhYrPSqtJNmcD', 'Binance', 'cex'),
        ('9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM', 'Binance 2', 'cex'),
        ('3yFwqXBfZY4jBVUafQ1YEXw189y2dN3V5KQq9uzBDy1E', 'OKX', 'cex'),

        -- DEXs
        ('JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4', 'Jupiter v6', 'dex'),
        ('whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc', 'Orca Whirlpool', 'dex'),
        ('675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8', 'Raydium AMM', 'dex'),

        -- Bridges
        ('worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth', 'Wormhole', 'bridge'),

        -- Issuers
        ('7q7QyjvMwf9szLMQ6aN1Y8DEF1ot3ueNQHN5G5C9pU2p', 'Circle (USDC)', 'issuer'),

        -- Protocols
        ('MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA', 'Marginfi', 'protocol'),
        ('KLend2g3cP87ber41NjFMWvHSZtLdEDqv8n8RP4MtJB', 'Kamino Lend', 'protocol'),
        ('So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo', 'Solend', 'protocol'),

        -- Market Makers
        ('5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1', 'Wintermute', 'market_maker')
    ) as t(wallet, label, category)
),

classified_wallets as (
    select
        ws.wallet,
        ws.token_symbol,
        ws.send_count,
        ws.receive_count,
        ws.total_tx_count,
        ws.send_volume,
        ws.receive_volume,
        ws.total_volume,
        ws.net_flow,
        ws.avg_transfer_size,
        ws.max_transfer,

        -- Classification logic
        case
            -- Known wallets first
            when kw.label is not null then kw.label
            -- Whale: large transfers or high volume
            when ws.max_transfer >= 100000 or ws.total_volume >= 1000000 then 'Whale'
            -- Bot: high frequency, small amounts
            when ws.total_tx_count >= 50 and ws.avg_transfer_size <= 1000 then 'Bot/MEV'
            -- Market Maker: high frequency, balanced activity
            when ws.total_tx_count >= 100
                and ws.send_count > 0 and ws.receive_count > 0
                and least(ws.send_count, ws.receive_count)::float / greatest(ws.send_count, ws.receive_count) >= 0.3
            then 'Market Maker'
            -- Retail: low activity
            when ws.total_tx_count <= 10 and ws.total_volume <= 10000 then 'Retail'
            -- Trader: active but not classified
            when ws.total_tx_count > 10 then 'Trader'
            else 'Unknown'
        end as wallet_label,

        case
            when kw.category is not null then kw.category
            when ws.max_transfer >= 100000 or ws.total_volume >= 1000000 then 'whale'
            when ws.total_tx_count >= 50 and ws.avg_transfer_size <= 1000 then 'bot'
            when ws.total_tx_count >= 100
                and ws.send_count > 0 and ws.receive_count > 0
                and least(ws.send_count, ws.receive_count)::float / greatest(ws.send_count, ws.receive_count) >= 0.3
            then 'market_maker'
            when ws.total_tx_count <= 10 and ws.total_volume <= 10000 then 'retail'
            when ws.total_tx_count > 10 then 'trader'
            else 'unknown'
        end as wallet_category,

        case
            when kw.label is not null then 1.0
            when ws.max_transfer >= 100000 or ws.total_volume >= 1000000 then 0.8
            when ws.total_tx_count >= 50 and ws.avg_transfer_size <= 1000 then 0.7
            when ws.total_tx_count >= 100 then 0.6
            when ws.total_tx_count <= 10 then 0.5
            else 0.0
        end as confidence,

        case
            when kw.label is not null then 'known'
            else 'behavior'
        end as classification_source

    from wallet_stats ws
    left join known_wallets kw on ws.wallet = kw.wallet
)

select
    wallet,
    token_symbol,
    wallet_label,
    wallet_category,
    confidence,
    classification_source,
    send_count,
    receive_count,
    total_tx_count,
    send_volume,
    receive_volume,
    total_volume,
    net_flow,
    avg_transfer_size,
    max_transfer,
    -- Rank within category
    row_number() over (partition by token_symbol, wallet_category order by total_volume desc) as category_rank,
    current_timestamp as updated_at

from classified_wallets
