"""
Health Check Endpoints

Comprehensive health monitoring for production deployment.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import psutil
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


# Track application start time
START_TIME = time.time()


@router.get("")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check - returns 200 if application is running.
    Used by Docker HEALTHCHECK and load balancers.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - START_TIME)
    }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with system metrics.
    """
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        uptime = int(time.time() - START_TIME)
        
        # Health status
        is_healthy = True
        issues = []
        
        # Check CPU
        if cpu_percent > 90:
            is_healthy = False
            issues.append(f"High CPU usage: {cpu_percent}%")
        
        # Check memory
        if memory.percent > 90:
            is_healthy = False
            issues.append(f"High memory usage: {memory.percent}%")
        
        # Check disk
        if disk.percent > 90:
            is_healthy = False
            issues.append(f"High disk usage: {disk.percent}%")
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime,
            "system": {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory.percent, 2),
                "memory_available_mb": round(memory.available / (1024 * 1024), 2),
                "disk_percent": round(disk.percent, 2),
                "disk_free_gb": round(disk.free / (1024**3), 2)
            },
            "issues": issues
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database")
async def database_health_check() -> Dict[str, Any]:
    """
    Database connectivity health check.
    """
    from ..core.database import AsyncSessionLocal
    
    try:
        # Test database connection
        start = time.time()
        async with AsyncSessionLocal() as session:
            result = await session.execute("SELECT 1")
            result.scalar()
        
        latency_ms = (time.time() - start) * 1000
        
        return {
            "status": "healthy",
            "database": "postgresql",
            "latency_ms": round(latency_ms, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "postgresql",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/redis")
async def redis_health_check() -> Dict[str, Any]:
    """
    Redis connectivity health check.
    """
    import redis
    import os
    
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = redis.from_url(redis_url)
        
        # Test connection
        start = time.time()
        client.ping()
        latency_ms = (time.time() - start) * 1000
        
        # Get info
        info = client.info()
        
        return {
            "status": "healthy",
            "redis": {
                "version": info.get('redis_version'),
                "connected_clients": info.get('connected_clients'),
                "used_memory_mb": round(info.get('used_memory', 0) / (1024 * 1024), 2),
                "latency_ms": round(latency_ms, 2)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/exchange")
async def exchange_health_check() -> Dict[str, Any]:
    """
    Exchange connectivity health check.
    """
    from ..data.binance_client import BinanceClient
    
    try:
        client = BinanceClient()
        
        # Test connection
        start = time.time()
        server_time = await client.get_server_time()
        latency_ms = (time.time() - start) * 1000
        
        return {
            "status": "healthy",
            "exchange": "binance",
            "server_time": server_time,
            "latency_ms": round(latency_ms, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Exchange health check failed: {e}")
        return {
            "status": "unhealthy",
            "exchange": "binance",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/providers")
async def providers_status() -> Dict[str, Any]:
    """Get detailed provider status"""
    providers = {
        "truedata": {"healthy": False, "status": "unknown"},
        "zerodha": {"healthy": False, "status": "unknown"}
    }
    
    # Check TrueData
    try:
        from data.truedata_client import truedata_client
        if hasattr(truedata_client, 'is_available'):
            providers["truedata"]["healthy"] = truedata_client.is_available()
            if hasattr(truedata_client, 'subscription_expired') and truedata_client.subscription_expired:
                providers["truedata"]["status"] = "Subscription expired"
            elif providers["truedata"]["healthy"]:
                providers["truedata"]["status"] = "Connected"
            else:
                providers["truedata"]["status"] = "Disconnected"
        else:
            providers["truedata"]["status"] = "Status unknown"
    except Exception as e:
        providers["truedata"]["status"] = f"Error: {str(e)[:50]}"
    
    # Check Zerodha
    try:
        from brokers.zerodha import zerodha_client
        if hasattr(zerodha_client, 'kite') and zerodha_client.kite is not None:
            try:
                profile = zerodha_client.kite.profile()
                providers["zerodha"]["healthy"] = True
                providers["zerodha"]["status"] = f"Connected ({profile.get('user_name', 'Unknown')})"
            except Exception as e:
                providers["zerodha"]["healthy"] = False
                if "token" in str(e).lower() or "unauthorized" in str(e).lower():
                    providers["zerodha"]["status"] = "Token invalid or expired"
                else:
                    providers["zerodha"]["status"] = f"Error: {str(e)[:50]}"
        else:
            providers["zerodha"]["status"] = "Client not initialized"
    except Exception as e:
        providers["zerodha"]["status"] = f"Error: {str(e)[:50]}"
    
    return {
        "providers": providers,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/readiness")
@router.get("/ready")  # Add /ready alias for compatibility
async def readiness_check() -> Dict[str, Any]:
    """
    Kubernetes readiness probe - checks if app is ready to serve traffic.
    FIXED: Now checks provider status and returns 503 if unavailable
    """
    checks = {
        "database": False,
        "redis": False,
        "system": False,
        "truedata": False,
        "zerodha": False
    }
    
    issues = []
    
    try:
        # Check database
        db_health = await database_health_check()
        checks["database"] = db_health.get("status") == "healthy"
        if not checks["database"]:
            issues.append("Database unavailable")
        
        # Check Redis
        redis_health = await redis_health_check()
        checks["redis"] = redis_health.get("status") == "healthy"
        if not checks["redis"]:
            issues.append("Redis unavailable")
        
        # Check system resources
        memory = psutil.virtual_memory()
        checks["system"] = memory.percent < 95  # Not critically low on memory
        if not checks["system"]:
            issues.append(f"Low memory: {memory.percent}%")
        
        # Check TrueData provider
        try:
            from data.truedata_client import truedata_client
            if hasattr(truedata_client, 'is_available'):
                checks["truedata"] = truedata_client.is_available()
                if hasattr(truedata_client, 'subscription_expired') and truedata_client.subscription_expired:
                    issues.append("TrueData: Subscription expired")
                elif not checks["truedata"]:
                    issues.append("TrueData: Disconnected")
        except Exception as e:
            issues.append(f"TrueData: {str(e)[:50]}")
        
        # Check Zerodha broker
        try:
            from brokers.zerodha import zerodha_client
            if hasattr(zerodha_client, 'kite') and zerodha_client.kite is not None:
                checks["zerodha"] = True
            else:
                issues.append("Zerodha: Client not initialized")
        except Exception as e:
            issues.append(f"Zerodha: {str(e)[:50]}")
        
        # Critical services: database + redis
        critical_ok = checks["database"] and checks["redis"]
        
        # At least ONE data provider must be healthy
        data_provider_ok = checks["truedata"] or checks["zerodha"]
        
        if not critical_ok:
            logger.error(f"❌ Critical services down: {issues}")
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "reason": "Critical services unavailable",
                    "checks": checks,
                    "issues": issues
                }
            )
        
        if not data_provider_ok:
            logger.error(f"❌ No data providers available: {issues}")
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "reason": "No data providers available",
                    "checks": checks,
                    "issues": issues
                }
            )
        
        return {
            "status": "ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "error": str(e)}
        )


@router.get("/liveness")
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes liveness probe - checks if app is alive and responding.
    Simple check that doesn't test dependencies.
    """
    try:
        # Just check if the process is responsive
        uptime = int(time.time() - START_TIME)
        
        return {
            "status": "alive",
            "uptime_seconds": uptime,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

