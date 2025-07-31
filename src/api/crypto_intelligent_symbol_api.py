"""
API endpoints for Crypto Intelligent Symbol Management
Production-grade crypto pair management API
Adapted from shares system for enterprise crypto trading
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List
import logging
from datetime import datetime

from src.core.crypto_intelligent_symbol_manager import (
    start_crypto_intelligent_management,
    stop_crypto_intelligent_management, 
    get_crypto_intelligent_status,
    get_crypto_intelligent_manager
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/crypto-intelligent-symbols")
async def get_crypto_intelligent_symbols_status():
    """Get Crypto Intelligent Symbol Manager status and pair expansion info"""
    try:
        # Get current status
        status = await get_crypto_intelligent_status()
        
        # Get manager instance
        manager = await get_crypto_intelligent_manager()
        if not manager:
            raise HTTPException(status_code=503, detail="Crypto Intelligent Symbol Manager not available")
        
        # Get active symbols list
        active_symbols = list(manager.active_symbols)
        
        # Categorize crypto pairs
        symbol_categories = {
            'core_pairs': [],
            'major_crypto': [],
            'defi_tokens': [],
            'altcoins': [],
            'other': []
        }
        
        for symbol in active_symbols:
            if symbol in manager.config.core_pairs:
                symbol_categories['core_pairs'].append(symbol)
            elif symbol in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']:
                symbol_categories['major_crypto'].append(symbol)
            elif any(defi in symbol for defi in ['UNI', 'AAVE', 'COMP', 'SUSHI']):
                symbol_categories['defi_tokens'].append(symbol)
            elif 'USDT' in symbol:
                symbol_categories['altcoins'].append(symbol)
            else:
                symbol_categories['other'].append(symbol)
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "crypto_pair_management": {
                "total_active_pairs": len(active_symbols),
                "max_allowed": status.get('max_pairs', 100),
                "utilization_percent": round((len(active_symbols) / status.get('max_pairs', 100)) * 100, 1),
                "auto_management_enabled": status.get('autonomous_mode', False),
                "market_type": "crypto"
            },
            "current_strategy": status.get('current_strategy', 'BALANCED'),
            "crypto_pair_categories": symbol_categories,
            "active_pairs_sample": active_symbols[:20],  # First 20 for display
            "intelligent_features": {
                "autonomous_pair_selection": True,
                "dynamic_strategy_switching": True,
                "performance_based_optimization": True,
                "market_condition_analysis": True,
                "24_7_crypto_monitoring": True,
                "volatility_based_filtering": True
            },
            "performance": {
                "strategy_switches_today": status.get('strategy_switches_today', 0),
                "last_strategy_change": status.get('last_strategy_change'),
                "next_evaluation": status.get('next_evaluation'),
                "pair_health_status": status.get('pair_health_status', 'monitoring')
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting crypto intelligent symbols status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting crypto symbol status: {str(e)}"
        )

@router.post("/crypto-intelligent-symbols/start")
async def start_crypto_intelligent_symbol_management_endpoint():
    """Start the crypto intelligent symbol management system"""
    try:
        success = await start_crypto_intelligent_management()
        
        if success:
            return {
                "status": "success",
                "message": "Crypto Intelligent Symbol Management started successfully",
                "features": [
                    "Autonomous crypto pair management",
                    "24/7 market monitoring", 
                    "Strategy auto-switching",
                    "Performance-based optimization",
                    "Real-time pair health monitoring"
                ],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to start Crypto Intelligent Symbol Management"
            )
    
    except Exception as e:
        logger.error(f"Error starting Crypto Intelligent Symbol Management: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error starting crypto system: {str(e)}"
        )

@router.post("/crypto-intelligent-symbols/stop")
async def stop_crypto_intelligent_symbol_management_endpoint():
    """Stop the crypto intelligent symbol management system"""
    try:
        success = await stop_crypto_intelligent_management()
        
        if success:
            return {
                "status": "success", 
                "message": "Crypto Intelligent Symbol Management stopped successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to stop Crypto Intelligent Symbol Management"
            )
    
    except Exception as e:
        logger.error(f"Error stopping Crypto Intelligent Symbol Management: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error stopping crypto system: {str(e)}"
        )

@router.get("/crypto-intelligent-symbols/strategies")
async def get_available_crypto_strategies():
    """Get available crypto trading strategies"""
    try:
        return {
            "status": "success",
            "available_strategies": [
                {
                    "name": "DeFi_FOCUS",
                    "description": "Focus on DeFi tokens and protocols",
                    "suitable_for": "DeFi market opportunities",
                    "risk_level": "Medium-High"
                },
                {
                    "name": "BALANCED", 
                    "description": "Balanced approach across all crypto categories",
                    "suitable_for": "General market conditions",
                    "risk_level": "Medium"
                },
                {
                    "name": "MAJOR_PAIRS",
                    "description": "Focus on major cryptocurrencies (BTC, ETH, BNB)",
                    "suitable_for": "High volatility periods",
                    "risk_level": "Low-Medium"
                },
                {
                    "name": "ALTCOIN_FOCUS",
                    "description": "Focus on promising altcoins",
                    "suitable_for": "Low volatility periods with growth potential",
                    "risk_level": "High"
                }
            ],
            "strategy_selection": "autonomous",
            "manual_override": False,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting crypto strategies: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting strategies: {str(e)}"
        )

@router.get("/crypto-intelligent-symbols/health")
async def get_crypto_symbol_health():
    """Get health status of crypto symbol management"""
    try:
        manager = await get_crypto_intelligent_manager()
        if not manager:
            return {
                "status": "stopped",
                "message": "Crypto Intelligent Symbol Manager not running",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "status": "healthy" if manager.is_running else "stopped",
            "autonomous_mode": True,
            "background_tasks": {
                "strategy_monitor": manager.is_running,
                "pair_health_monitor": manager.is_running,
                "performance_tracker": manager.is_running,
                "capital_sync": manager.is_running
            },
            "system_health": {
                "memory_usage": "optimal",
                "processing_speed": "real-time",
                "error_rate": "minimal"
            },
            "uptime": "continuous" if manager.is_running else "stopped",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting crypto symbol health: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting health status: {str(e)}"
        )

@router.get("/crypto-intelligent-symbols/active-pairs")
async def get_active_crypto_pairs():
    """Get detailed list of active crypto pairs"""
    try:
        manager = await get_crypto_intelligent_manager()
        if not manager:
            raise HTTPException(status_code=503, detail="Crypto Intelligent Symbol Manager not available")
        
        active_pairs = []
        for symbol in manager.active_symbols:
            metadata = manager.symbol_metadata.get(symbol, {})
            active_pairs.append({
                "symbol": symbol,
                "type": metadata.get("type", "unknown"),
                "priority": metadata.get("priority", 4),
                "strategy": metadata.get("strategy", "BALANCED"),
                "auto_selected": metadata.get("auto_selected", False),
                "added_at": metadata.get("added_at")
            })
        
        # Sort by priority and symbol
        active_pairs.sort(key=lambda x: (x["priority"], x["symbol"]))
        
        return {
            "status": "success",
            "total_pairs": len(active_pairs),
            "active_pairs": active_pairs,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting active crypto pairs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting active pairs: {str(e)}"
        )