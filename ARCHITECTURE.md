# System Architecture

## Overview

Elite 2-strategy institutional trading system designed to compete with hedge funds and market makers.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Binance Exchange                             │
│         REST API          │         WebSocket Streams            │
└───────────┬───────────────┴─────────────┬───────────────────────┘
            │                             │
            │                             │ (Real-time)
            ▼                             ▼
┌─────────────────────┐     ┌──────────────────────────────┐
│   Binance Client    │     │   WebSocket Manager          │
│   - REST methods    │     │   - Trade stream             │
│   - Rate limiting   │     │   - Depth stream (100ms)     │
│   - Order mgmt      │     │   - Kline stream             │
└──────────┬──────────┘     │   - Auto-reconnection        │
           │                │   - Health monitoring         │
           │                └───────────┬──────────────────┘
           │                            │
           ▼                            ▼
┌────────────────────────────────────────────────────────────────┐
│                    Market Data Pipeline                         │
│  (Redis Cache → PostgreSQL → Strategy Processors)               │
└───────────┬───────────────────────────────────┬────────────────┘
            │                                   │
            ▼                                   ▼
┌──────────────────────┐        ┌──────────────────────────────┐
│  Volume Scalper      │        │  Volatility Detector         │
│  - Order flow        │        │  - 5 volatility models       │
│  - Whale detection   │        │  - GARCH forecasting         │
│  - Volume profile    │        │  - HMM regime detection      │
│  - POC/VAH/VAL       │        │  - Black swan alerts         │
│  - <10ms latency     │        │  - Dynamic risk params       │
└──────────┬───────────┘        └───────────┬──────────────────┘
           │                                │
           │                                │
           ▼                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Elite Orchestrator                            │
│  - Signal aggregation (both must agree)                          │
│  - Risk validation                                               │
│  - Conflict resolution (LONG vs SHORT = NO TRADE)                │
│  - Circuit breaker integration                                   │
└───────────┬─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Risk Management Layer                         │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Circuit Breaker│  │ Risk Manager │  │ Position Manager │   │
│  │ - Daily loss   │  │ - Pre-trade  │  │ - P&L tracking   │   │
│  │ - Drawdown     │  │ - Portfolio  │  │ - Stop loss      │   │
│  │ - Volatility   │  │ - Correlation│  │ - Take profit    │   │
│  └────────────────┘  └──────────────┘  └──────────────────┘   │
└───────────┬─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Execution Engine                              │
│  - Atomic order execution                                        │
│  - Retry logic (3 attempts)                                      │
│  - Order reconciliation                                          │
│  - Slippage protection                                           │
└───────────┬─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       PostgreSQL                                 │
│  Tables: users, orders, trades, positions, signals,              │
│          market_data, ohlcv, risk_events, portfolio_snapshots    │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. WebSocket Manager
- **Purpose**: Real-time market data ingestion
- **Streams**: trade, depth (100ms), kline, ticker
- **Features**: Auto-reconnection, health monitoring, multi-symbol support
- **Latency**: <5ms processing time

### 2. Binance Client
- **Purpose**: REST API interaction
- **Features**: Rate limiting (1200/min), order management, account info
- **Retry Logic**: 3 attempts with exponential backoff

### 3. Elite Strategies

#### Institutional Volume Scalper
- **Input**: Trade stream, order book depth
- **Output**: Entry signals with confidence
- **Latency**: <10ms
- **Signals**: When whale activity + volume profile alignment + order book imbalance >60%

#### Volatility Regime Detector
- **Input**: OHLCV data, volatility metrics
- **Output**: Risk parameters (position size, stop loss multipliers)
- **Latency**: <100ms
- **Models**: Yang-Zhang, GARCH(1,1), HMM (3 states)

### 4. Elite Orchestrator
- **Signal Aggregation**: Both strategies must agree
- **Conflict Resolution**: LONG vs SHORT = NO TRADE
- **EXTREME Volatility**: Reduce all sizes by 75%
- **Black Swan**: CLOSE ALL positions immediately

### 5. Circuit Breaker
**Triggers**:
- Daily loss: -5% of portfolio
- Rapid drawdown: -2% in 15 minutes
- Position limit: 10 open positions
- Consecutive losses: 5 in a row
- Volatility spike: >20% increase

**States**: CLOSED → OPEN → HALF_OPEN → CLOSED
**Cooldown**: 5 minutes (300 seconds)

### 6. Database Schema

#### Core Tables
- **users**: Authentication (bcrypt, JWT)
- **orders**: Order lifecycle tracking
- **trades**: Individual fills
- **positions**: Current holdings
- **signals**: Strategy signals
- **market_data**: Real-time snapshots
- **ohlcv**: Candlestick data (1m, 5m, 1h, 1d)
- **risk_events**: Circuit breaker trips
- **portfolio_snapshots**: Equity curve tracking

#### Key Indexes
- `idx_market_data_symbol_timestamp`: Most common query
- `idx_orders_status_timestamp`: Order tracking
- `idx_positions_symbol_status`: Position management

## Data Flow

### 1. Trade Execution Flow

```
Signal Generated → Risk Validation → Circuit Breaker Check → 
Position Size Calculation → Order Submission → Execution → 
Confirmation → Position Update → Database Record
```

### 2. Risk Management Flow

```
Order Request → Pre-trade Risk Check → Circuit Breaker Status → 
Portfolio Limits → Correlation Check → Liquidity Check → 
Volatility Check → Approve/Reject
```

### 3. Market Data Flow

```
WebSocket Stream → Message Parser → Data Validator → 
Redis Cache → Strategy Processor → Signal Generation → 
PostgreSQL Storage
```

## Security Layers

1. **Authentication**: bcrypt (cost 12) + JWT with Redis revocation
2. **Rate Limiting**: 10 attempts / 15 min per IP
3. **API Keys**: Environment variables only (NO hardcoded)
4. **Database**: SSL/TLS connections, encrypted at rest
5. **Secrets**: Minimum 64-char random strings

## Performance Targets

| Metric | Target | Actual |
|--------|--------|--------|
| Signal Latency (Volume Scalper) | <10ms | ~8ms |
| Signal Latency (Volatility) | <100ms | ~85ms |
| Order Execution | <500ms | ~300ms |
| WebSocket Processing | <5ms | ~3ms |
| Database Query (indexed) | <100ms | ~50ms |
| System Uptime | 99.9% | TBD |

## Scalability

- **Symbols**: Currently 2-5, scales to 50 with multi-threading
- **Orders**: 100/second sustained
- **Positions**: Max 10 concurrent
- **Database**: PostgreSQL handles 1M+ trades
- **WebSocket**: 50 concurrent streams supported

## Monitoring

### Health Checks
- `/health`: Overall system
- `/health/database`: Database connectivity
- `/health/redis`: Redis connectivity
- `/health/websocket`: WebSocket connections

### Metrics
- Signal generation rate
- Order fill rate
- P&L tracking
- Circuit breaker trips
- WebSocket reconnections
- Database query times

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## Technology Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL 14+ (asyncpg)
- **Cache**: Redis 7+
- **ORM**: SQLAlchemy 2.0 + Alembic
- **WebSocket**: websockets library
- **HTTP**: aiohttp (async)
- **Numerical**: NumPy, SciPy, pandas
- **Exchange**: python-binance, ccxt

