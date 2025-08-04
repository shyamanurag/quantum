-- Migration: Add Missing Crypto Tables
-- Version: 005
-- Date: 2024-08-04
-- Description: Add symbols and market_cap_data tables to fix missing table errors

BEGIN;

-- Create symbols table for crypto assets
CREATE TABLE IF NOT EXISTS symbols (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    exchange VARCHAR(20) DEFAULT 'BINANCE',
    symbol_type VARCHAR(20) DEFAULT 'SPOT',
    base_asset VARCHAR(10),
    quote_asset VARCHAR(10),
    is_active BOOLEAN DEFAULT true,
    volume_24h DECIMAL(20,8) DEFAULT 0,
    price_change_24h DECIMAL(10,4) DEFAULT 0,
    keywords TEXT,  -- For news impact scalper
    min_qty DECIMAL(20,8) DEFAULT 0.00000001,
    max_qty DECIMAL(20,8) DEFAULT 1000000,
    step_size DECIMAL(20,8) DEFAULT 0.00000001,
    min_price DECIMAL(20,8) DEFAULT 0.00000001,
    max_price DECIMAL(20,8) DEFAULT 1000000,
    tick_size DECIMAL(20,8) DEFAULT 0.00000001,
    min_notional DECIMAL(20,8) DEFAULT 10,
    trading_status VARCHAR(20) DEFAULT 'TRADING',
    permissions JSONB DEFAULT '[]',
    filters JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create market_cap_data table for BTC dominance calculations
CREATE TABLE IF NOT EXISTS market_cap_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    btc_market_cap DECIMAL(30,2),
    total_market_cap DECIMAL(30,2),
    btc_dominance DECIMAL(8,4),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert initial crypto symbols for testnet
INSERT INTO symbols (symbol, name, exchange, base_asset, quote_asset, is_active, volume_24h, keywords) VALUES
('BTCUSDT', 'Bitcoin', 'BINANCE', 'BTC', 'USDT', true, 1000000000, 'bitcoin,btc,crypto,digital gold'),
('ETHUSDT', 'Ethereum', 'BINANCE', 'ETH', 'USDT', true, 500000000, 'ethereum,eth,smart contracts,defi'),
('BNBUSDT', 'Binance Coin', 'BINANCE', 'BNB', 'USDT', true, 100000000, 'binance,bnb,exchange token'),
('ADAUSDT', 'Cardano', 'BINANCE', 'ADA', 'USDT', true, 80000000, 'cardano,ada,proof of stake'),
('SOLUSDT', 'Solana', 'BINANCE', 'SOL', 'USDT', true, 60000000, 'solana,sol,fast blockchain'),
('DOTUSDT', 'Polkadot', 'BINANCE', 'DOT', 'USDT', true, 40000000, 'polkadot,dot,interoperability'),
('LINKUSDT', 'Chainlink', 'BINANCE', 'LINK', 'USDT', true, 30000000, 'chainlink,link,oracle,data'),
('AVAXUSDT', 'Avalanche', 'BINANCE', 'AVAX', 'USDT', true, 25000000, 'avalanche,avax,fast consensus')
ON CONFLICT (symbol) DO UPDATE SET
    name = EXCLUDED.name,
    keywords = EXCLUDED.keywords,
    volume_24h = EXCLUDED.volume_24h,
    updated_at = NOW();

-- Insert initial market cap data for BTC dominance
INSERT INTO market_cap_data (symbol, btc_market_cap, total_market_cap, btc_dominance, timestamp) VALUES
('BTC', 1000000000000, 2500000000000, 40.0, NOW()),
('TOTAL', 1000000000000, 2500000000000, 40.0, NOW())
ON CONFLICT DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_symbols_exchange_active ON symbols(exchange, is_active);
CREATE INDEX IF NOT EXISTS idx_symbols_volume ON symbols(volume_24h DESC);
CREATE INDEX IF NOT EXISTS idx_market_cap_timestamp ON market_cap_data(timestamp DESC);

COMMIT;