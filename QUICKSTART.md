# 🚀 QUICK START GUIDE

Get the Elite Trading System running in **5 minutes**!

---

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (or use Docker)
- Redis (or use Docker)
- Binance API keys

---

## Option 1: Docker Compose (Recommended)

### Step 1: Configure Environment
```bash
# Copy environment template
cp production.env.template .env

# Edit .env with your settings
nano .env
```

**Required variables:**
```bash
# Database
POSTGRES_PASSWORD=your_secure_password

# Binance API
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# JWT Secret
JWT_SECRET_KEY=your_random_secret_key

# Redis
REDIS_URL=redis://redis:6379/0
```

### Step 2: Start Production Stack
```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Step 3: Verify Health
```bash
# Check application health
curl http://localhost:8000/health

# Check detailed health
curl http://localhost:8000/health/detailed

# Check database
curl http://localhost:8000/health/database
```

### Step 4: Access Monitoring
- **API**: http://localhost:8000
- **Grafana**: http://localhost:3000 (admin/your_password)
- **Prometheus**: http://localhost:9090

---

## Option 2: Local Development

### Step 1: Install Dependencies
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
# Copy template
cp production.env.template .env

# Edit with your values
nano .env
```

### Step 3: Setup Database
```bash
# Run PostgreSQL (Docker)
docker run -d -p 5432:5432 \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=trading_system \
  postgres:15-alpine

# Run migrations
alembic upgrade head
```

### Step 4: Start Redis
```bash
# Run Redis (Docker)
docker run -d -p 6379:6379 redis:7-alpine
```

### Step 5: Start Application
```bash
# Development mode
python app.py

# Or production mode with Gunicorn
gunicorn app:app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker
```

---

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Integration Tests Only
```bash
pytest tests/integration/ -v
```

### With Coverage
```bash
pytest tests/ -v --cov=src --cov-report=html
```

---

## Configuration

### Basic Configuration
Edit `config/config.yaml`:
```yaml
trading:
  symbols:
    - BTCUSDT
    - ETHUSDT
  
  portfolio_value: 100000.0
  
  strategies:
    volume_scalper:
      enabled: true
      whale_threshold: 50000
      min_confidence: 0.7
    
    volatility_detector:
      enabled: true
      min_confidence: 0.7

risk:
  max_daily_loss_pct: 5.0
  max_position_size_pct: 10.0
```

### Enhancement Configuration
Defaults are production-ready, but you can adjust:

```python
# In orchestrator or strategy initialization
portfolio_value = 100000.0  # Your capital
min_signal_score = 75.0     # Higher = stricter (70-90)
kelly_fraction = 0.25       # Conservative Kelly (0.25-0.5)
max_risk_per_trade = 0.02   # 2% max risk per trade
```

---

## API Endpoints

### Authentication
```bash
# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"trader","password":"secure123","email":"trader@example.com"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"trader","password":"secure123"}'
```

### Health Checks
```bash
# Basic health
curl http://localhost:8000/health

# Detailed with metrics
curl http://localhost:8000/health/detailed

# Database status
curl http://localhost:8000/health/database

# Redis status
curl http://localhost:8000/health/redis

# Exchange connectivity
curl http://localhost:8000/health/exchange
```

### Trading (Authenticated)
```bash
# Get token from login, then:
TOKEN="your_jwt_token"

# View strategies
curl http://localhost:8000/api/strategies \
  -H "Authorization: Bearer $TOKEN"

# View positions
curl http://localhost:8000/api/positions \
  -H "Authorization: Bearer $TOKEN"

# View signals
curl http://localhost:8000/api/signals \
  -H "Authorization: Bearer $TOKEN"
```

---

## Monitoring

### Prometheus Metrics
Access at http://localhost:9090

Key metrics:
- `trading_signals_total` - Total signals generated
- `trading_executions_total` - Total trades executed
- `position_value_usd` - Current position values
- `system_health` - Overall system health

### Grafana Dashboards
Access at http://localhost:3000

Default dashboards:
- **Trading Overview**: Signals, executions, P&L
- **System Health**: CPU, memory, database
- **Strategy Performance**: Win rate, Sharpe ratio

### Logs
```bash
# Docker logs
docker-compose -f docker-compose.prod.yml logs -f trading-app

# Or view files
tail -f logs/trading-system.log
```

---

## Production Checklist

Before going live:

- [ ] Set strong passwords (Postgres, JWT secret)
- [ ] Configure real Binance API keys
- [ ] Set appropriate position sizes
- [ ] Test with paper trading first
- [ ] Configure alerts (Telegram/Discord)
- [ ] Set up backup strategy
- [ ] Monitor for 24-48 hours
- [ ] Start with small capital
- [ ] Enable all health checks
- [ ] Configure log rotation

---

## Troubleshooting

### Database Connection Failed
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql -h localhost -U postgres -d trading_system
```

### Redis Connection Failed
```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli ping
```

### Import Errors
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/path/to/quantum_crypto:$PYTHONPATH

# Or add to .env
echo 'PYTHONPATH=/app' >> .env
```

### Tests Failing
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run with verbose output
pytest tests/ -v -s
```

---

## Performance Tuning

### For High-Frequency Trading
```yaml
# config/config.yaml
performance:
  workers: 8  # More workers
  order_book_depth: 20  # Less depth
  signal_timeout_ms: 5  # Faster timeout
```

### For Better Accuracy
```yaml
performance:
  workers: 2  # Fewer workers
  order_book_depth: 100  # More depth
  signal_timeout_ms: 50  # More processing time
  min_signal_score: 80  # Higher quality bar
```

---

## Support & Documentation

- **Complete Guide**: `100_PERCENT_COMPLETE.md`
- **Architecture**: `ARCHITECTURE.md`
- **Deployment**: `DEPLOYMENT.md`
- **Enhancements**: `ENHANCEMENTS_COMPLETE.md`
- **Integration**: `src/strategies/enhancements/INTEGRATION_GUIDE.md`

---

## 🎯 You're Ready!

The Elite Trading System is now running. Monitor the dashboards and logs for the first few hours to ensure everything is working correctly.

**Happy Trading! 🚀**


