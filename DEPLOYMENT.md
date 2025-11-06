# Elite Trading System - Deployment Guide

## Prerequisites

- PostgreSQL 14+ (NO SQLite - production only)
- Redis 7+ (for token revocation & caching)
- Python 3.11+
- Docker & Docker Compose (optional)

## Environment Variables

Create `.env` file (copy from `.env.example`):

```bash
# Database (REQUIRED - NO fallbacks)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/trading_db

# Binance API (REQUIRED)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=true

# Security (REQUIRED - Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))")
JWT_SECRET_KEY=generate_64_char_secret
ENCRYPTION_KEY=generate_32_char_secret
SECRET_KEY=generate_64_char_secret

# Redis (REQUIRED)
REDIS_URL=redis://localhost:6379/0

# Risk Management
MAX_DAILY_LOSS_PCT=0.05  # 5%
MAX_RAPID_DRAWDOWN_PCT=0.02  # 2%
MAX_POSITIONS=10
CIRCUIT_BREAKER_COOLDOWN=300  # seconds

# Strategy Parameters
WHALE_THRESHOLD_USD=50000
MIN_VOLUME_CONFIDENCE=0.7
MIN_VOLATILITY_CONFIDENCE=0.7
```

## Database Setup

### 1. Create PostgreSQL Database

```bash
psql -U postgres
CREATE DATABASE trading_db;
CREATE USER trading_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
\q
```

### 2. Run Migrations

```bash
# Install dependencies
pip install -r requirements.txt

# Run Alembic migrations
alembic upgrade head
```

### 3. Create Admin User (via API)

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "CHANGE_THIS_SECURE_PASSWORD",
    "email": "admin@example.com",
    "role": "admin"
  }'
```

## Running the System

### Development

```bash
# Start Redis
redis-server

# Start PostgreSQL (if not running)
pg_ctl start

# Run trading system
uvicorn main:app --reload --port 8000
```

### Production

```bash
# Using gunicorn with uvicorn workers
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

### Docker

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f trading-app

# Stop
docker-compose down
```

## Health Checks

```bash
# System health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/database

# Trading status
curl http://localhost:8000/api/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Monitoring

### Key Metrics

- **Latency**: Signal generation <10ms (Volume Scalper), <100ms (Volatility Detector)
- **Uptime**: Target 99.9%
- **Circuit Breaker**: Monitor trip frequency
- **Daily P&L**: Track against -5% limit
- **Position Count**: Monitor against limit (10)

### Alerts

Set up alerts for:
- Circuit breaker trips
- Daily loss >3%
- Database connection failures
- WebSocket disconnections >5 minutes
- Order execution failures >10%

## Security Checklist

- [ ] NO default credentials (users_db is empty)
- [ ] Strong JWT secrets (64+ chars, random)
- [ ] bcrypt cost factor 12
- [ ] Rate limiting enabled (10/15min per IP)
- [ ] Redis token revocation active
- [ ] PostgreSQL password secured
- [ ] Binance API keys from environment only
- [ ] HTTPS/TLS in production
- [ ] Regular security audits

## Backup & Recovery

### Database Backup

```bash
# Daily backup
pg_dump -U trading_user trading_db > backup_$(date +%Y%m%d).sql

# Restore
psql -U trading_user trading_db < backup_20250114.sql
```

### Configuration Backup

```bash
# Backup .env (encrypted)
gpg -c .env

# Restore
gpg .env.gpg
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready

# Check connection string
psql $DATABASE_URL

# Verify credentials
SELECT current_user, current_database();
```

### WebSocket Connection Issues

```bash
# Test Binance connection
curl https://api.binance.com/api/v3/ping

# Check WebSocket
wscat -c wss://stream.binance.com:9443/ws/btcusdt@trade
```

### Circuit Breaker Tripped

1. Check `/api/risk/circuit-breaker/status`
2. Review trip reason
3. Verify conditions improved
4. Manual reset if needed: `/api/risk/circuit-breaker/reset`

## Performance Tuning

### PostgreSQL

```sql
-- Optimize for trading workload
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
```

### Redis

```bash
# Optimize for caching
maxmemory 256mb
maxmemory-policy allkeys-lru
```

## Production Deployment (DigitalOcean)

See [README.md](README.md) for DigitalOcean App Platform deployment.

## Support

- Documentation: `/docs` (Swagger UI)
- Architecture: `ARCHITECTURE.md`
- Strategies: `STRATEGIES.md`

