"""API package initialization with comprehensive router integration"""

from fastapi import APIRouter
from . import (
    auth,
    market,
    dashboard_api,
    autonomous_trading,
    system_health,
    monitoring,
    user_management,
    order_management,
    position_management,
    trade_management,  # Add trade management router
    risk_management,
    signals,
    webhooks,
    websocket,  # Add WebSocket router
    crypto_market_data,  # Added real crypto data router
    # Additional routers
    database_health,
    error_monitoring,
    trading_control,
    market_data,
    users,
    daily_auth_workflow,
    simple_daily_auth,
    strategy_management,
    performance,
    # recommendations,  # Temporarily disabled due to circular import
    digital_ocean_logs  # Added real-time log monitoring
)

# Create main API router
api_router = APIRouter(prefix="/api")

# Include all routers with proper prefixes and tags
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(market.router, prefix="/market", tags=["Market Data"])
api_router.include_router(dashboard_api.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(autonomous_trading.router, prefix="/trading", tags=["Trading"])
api_router.include_router(system_health.router, prefix="/health", tags=["System Health"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
api_router.include_router(user_management.router, prefix="/users", tags=["User Management"])
api_router.include_router(order_management.router, prefix="/orders", tags=["Order Management"])
api_router.include_router(position_management.router, prefix="/positions", tags=["Position Management"])
api_router.include_router(trade_management.router, prefix="/trades", tags=["Trade Management"])  # Add trade management router
api_router.include_router(risk_management.router, prefix="/risk", tags=["Risk Management"])
api_router.include_router(signals.router, prefix="/signals", tags=["Trading Signals"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])  # Add WebSocket router
# Include crypto market data router with REAL Binance data
api_router.include_router(crypto_market_data.router, tags=["Crypto Market Data - REAL"])

# Additional router includes
api_router.include_router(database_health.router, prefix="/db-health", tags=["Database Health"])
api_router.include_router(error_monitoring.router, prefix="/errors", tags=["Error Monitoring"])
api_router.include_router(trading_control.router, prefix="/control", tags=["Trading Control"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["Market Data"])
api_router.include_router(users.router, tags=["Users"])
api_router.include_router(daily_auth_workflow.router, prefix="/daily-auth", tags=["Daily Auth Workflow"])
api_router.include_router(simple_daily_auth.router, prefix="/simple-auth", tags=["Simple Daily Auth"])
api_router.include_router(strategy_management.router, prefix="/strategies", tags=["Strategy Management"])
api_router.include_router(performance.router, prefix="/performance", tags=["Performance"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])

# Include Digital Ocean logs monitoring API  
api_router.include_router(digital_ocean_logs.router, prefix="/do-logs", tags=["Digital Ocean Logs"])

__all__ = ["api_router"]