# 🚀 Digital Ocean Deployment Guide
## Quantum Crypto Trading System

This guide provides step-by-step instructions for deploying to Digital Ocean using your managed databases.

## 📋 Pre-Deployment Setup

### ✅ Your Digital Ocean Resources (Already Created)

**✅ PostgreSQL Database:**
- Host: `quantum-do-user-23093341-0.g.db.ondigitalocean.com`
- Port: `25060`
- Database: `defaultdb`
- User: `doadmin`
- Password: `AVNS_8hBXKk-VUdKxoy9IVNB`
- SSL: Required

**✅ Redis Cache:**
- Host: `cachequantum-do-user-23093341-0.g.db.ondigitalocean.com`
- Port: `25061`
- User: `default`
- Password: `AVNS_XGsjxUE8pWuMIlwOoJa`

## 🔐 Step 1: Generate Secure Keys

Run the key generator to create production-safe secrets:

```bash
python generate_secure_keys.py
```

**Sample Output:**
```
JWT_SECRET=A7k9mP2nQ4rS8tU1vW3xY6zB5cE8fH0jL3nP6qT9uX2yA5dG8hK1mR4sV7wZ0bF4
ENCRYPTION_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
SECRET_KEY=X9yB2cE5fH8jK1nP4qS7vW0zA3dG6hL9mR2uX5yB8cF1nQ4tW7zA0dH3kM6pS9v
WEBHOOK_SECRET=P3qT6wZ9cF2gJ5mR8uX1bE4hK7nQ0tW3zA6dH9kM2pS5vY8cF1gJ4mR7uX0bE3h
```

## 🚀 Step 2: Deploy to Digital Ocean App Platform

### Option A: App Platform (Recommended)

1. **Create New App:**
   - Go to Digital Ocean Console → Apps
   - Click "Create App"
   - Connect to GitHub repository: `https://github.com/shyamanurag/quantum`

2. **Configure Environment Variables:**
   Copy from `do_app_platform_env.txt` and update:

   ```
   DATABASE_URL=postgresql://doadmin:AVNS_8hBXKk-VUdKxoy9IVNB@quantum-do-user-23093341-0.g.db.ondigitalocean.com:25060/defaultdb?sslmode=require
   REDIS_URL=redis://default:AVNS_XGsjxUE8pWuMIlwOoJa@cachequantum-do-user-23093341-0.g.db.ondigitalocean.com:25061
   JWT_SECRET=<your-generated-jwt-secret>
   ENCRYPTION_KEY=<your-generated-encryption-key>
   SECRET_KEY=<your-generated-session-secret>
   BINANCE_API_KEY=<your-binance-api-key>
   BINANCE_API_SECRET=<your-binance-api-secret>
   CORS_ORIGINS=["https://your-app-domain.ondigitalocean.app"]
   ```

3. **App Configuration:**
   - **Plan:** Professional ($12/month minimum for 1GB RAM)
   - **Region:** Choose closest to your users
   - **Build Command:** `pip install -r requirements.txt`
   - **Run Command:** `python app.py`
   - **Port:** `8000`

### Option B: Droplet Deployment

1. **Create Droplet:**
   - Image: Ubuntu 22.04 LTS
   - Plan: Basic $24/month (4GB RAM, 2 vCPUs)
   - Region: NYC3 or closest to databases

2. **Setup Droplet:**
   ```bash
   # SSH into your droplet
   ssh root@your-droplet-ip
   
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   
   # Clone repository
   git clone https://github.com/shyamanurag/quantum.git
   cd quantum
   ```

3. **Configure Environment:**
   ```bash
   # Copy the environment file
   cp digital_ocean_env_variables.txt .env
   
   # Edit with your secure keys
   nano .env
   # Update JWT_SECRET, ENCRYPTION_KEY, SECRET_KEY with generated values
   # Update BINANCE_API_KEY and BINANCE_API_SECRET with your keys
   # Update CORS_ORIGINS with your domain
   ```

4. **Deploy with Docker:**
   ```bash
   # Build and start services
   docker-compose up -d
   
   # Check status
   docker-compose ps
   
   # View logs
   docker-compose logs -f trading-app
   ```

## 🔍 Step 3: Verify Deployment

### Health Checks

```bash
# App Platform
curl https://your-app-name.ondigitalocean.app/health

# Droplet
curl http://your-droplet-ip:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-31T10:30:00Z",
  "database_connected": true,
  "redis_connected": true,
  "orchestrator_initialized": true
}
```

### Test Authentication

```bash
# Test login
curl -X POST https://your-app-domain/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

## 📊 Step 4: Setup Monitoring (Droplet Only)

Access monitoring services:

- **Grafana:** `http://your-droplet-ip:3000`
  - Username: `admin`
  - Password: `secure_grafana_password_2024`

- **Prometheus:** `http://your-droplet-ip:9090`

## 🔒 Step 5: Security Configuration

### SSL/TLS (App Platform)
- Automatically handled by Digital Ocean
- Custom domain SSL available

### SSL/TLS (Droplet)
```bash
# Install Certbot
sudo apt install certbot

# Get SSL certificate
sudo certbot certonly --standalone -d yourdomain.com

# Configure Nginx (included in docker-compose)
```

### Firewall (Droplet)
```bash
# Configure UFW
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8000
sudo ufw enable
```

## 🎯 Step 6: Trading Configuration

### Paper Trading Mode (CURRENT CONFIGURATION - FULLY AUTONOMOUS)
```bash
# Current safe configuration for autonomous crypto trading:
TRADING_MODE=paper
PAPER_TRADING=true
BINANCE_TESTNET=true
ENABLE_AUTONOMOUS_TRADING=true
```

### For Live Trading (After Testing Paper Trading)
```bash
# Switch to live trading after successful paper trading:
TRADING_MODE=production
PAPER_TRADING=false
BINANCE_TESTNET=false
ENABLE_AUTONOMOUS_TRADING=true
```

## 📱 Step 7: Frontend Deployment

### Deploy React Frontend
```bash
# In frontend directory
cd frontend
npm install
npm run build

# Deploy build to DO Spaces or serve via Nginx
```

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Failed:**
   ```bash
   # Check SSL requirement
   DATABASE_URL=postgresql://doadmin:password@host:25060/defaultdb?sslmode=require
   ```

2. **Redis Connection Failed:**
   ```bash
   # Ensure Redis URL format is correct
   REDIS_URL=redis://username:password@host:25061
   ```

3. **App Platform Build Failed:**
   - Check Python version in runtime.txt
   - Verify requirements.txt includes all dependencies

### Logs

**App Platform:**
- View logs in DO Console → Apps → Your App → Runtime Logs

**Droplet:**
```bash
docker-compose logs -f trading-app
tail -f logs/trading_system.log
```

## 📞 Support Checklist

Before going live, verify:

- [ ] ✅ Health endpoint returns 200 OK
- [ ] 🔐 Authentication working (login/logout)
- [ ] 🗄️ Database queries successful
- [ ] 🔴 Redis cache operational
- [ ] 📊 Monitoring dashboards accessible
- [ ] 🔑 All API keys configured
- [ ] 🌐 CORS configured for your domain
- [ ] 🔒 SSL/TLS certificate active
- [ ] 📈 Trading mode set appropriately

## 🎉 Success Indicators

Your deployment is successful when:

- ✅ All health checks pass
- ✅ Trading system initializes without errors
- ✅ Database connections stable
- ✅ Redis cache responding
- ✅ Authentication flow working
- ✅ API endpoints accessible
- ✅ Monitoring metrics collecting

**Congratulations! Your Quantum Crypto Trading System is live on Digital Ocean! 🚀💎**