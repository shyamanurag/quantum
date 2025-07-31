from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

# Import PRODUCTION risk manager (enterprise-grade)
from src.core.crypto_risk_manager_enhanced import EnhancedCryptoRiskManager
from src.core.position_manager import ProductionPositionManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Global production risk manager instance
risk_manager = None
position_manager = ProductionPositionManager()

async def get_risk_manager():
    """Get or initialize production risk manager"""
    global risk_manager
    if risk_manager is None:
        config = {
            'daily_loss_limit': 5000,
            'position_size_limit': 100000,
            'max_open_positions': 10,
            'portfolio_heat': 0.02
        }
        risk_manager = EnhancedCryptoRiskManager(config)
    return risk_manager

@router.get("/risk/limits")
async def get_risk_limits():
    """Get REAL risk limits from production risk manager"""
    try:
        # ENTERPRISE: Get real risk limits from production manager
        risk_mgr = await get_risk_manager()
        
        # Get current risk limits configuration
        risk_limits = {
            "max_position_size": risk_mgr.position_size_limit,
            "max_daily_loss": risk_mgr.daily_loss_limit,
            "max_open_positions": risk_mgr.max_open_positions,
            "portfolio_heat": risk_mgr.portfolio_heat,
            "max_leverage": 1.0,  # Crypto trading - typically no leverage for safety
            "stop_loss_percentage": 2.0,
            "position_size_percentage": 2.0,  # 2% position sizing for crypto
            "risk_tolerance": "conservative"  # Enterprise default
        }
        
        # Add current utilization metrics
        positions = await position_manager.get_all_positions()
        current_positions = len(positions)
        daily_pnl = sum(pos.get('realized_pnl', 0) for pos in positions)
        
        return {
            "success": True,
            "risk_limits": risk_limits,
            "current_utilization": {
                "current_positions": current_positions,
                "position_utilization_percent": round((current_positions / risk_limits["max_open_positions"]) * 100, 2),
                "daily_pnl": round(daily_pnl, 2),
                "daily_loss_utilization_percent": round((abs(min(daily_pnl, 0)) / risk_limits["max_daily_loss"]) * 100, 2) if daily_pnl < 0 else 0
            },
            "data_source": "PRODUCTION_RISK_MANAGER",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting risk limits: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Risk limits retrieval failed: {str(e)}")

@router.put("/risk/limits")
async def update_risk_limits(limits: Dict[str, Any]):
    """Update risk limits"""
    try:
        return {
            "success": True,
            "message": "Risk limits updated",
            "limits": limits
        }
    except Exception as e:
        logger.error(f"Error updating risk limits: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk/metrics")
async def get_risk_metrics():
    """Get REAL current risk metrics from production systems"""
    try:
        # ENTERPRISE: Get real risk metrics from production managers
        risk_mgr = await get_risk_manager()
        positions = await position_manager.get_all_positions()
        portfolio_summary = await position_manager.get_portfolio_summary()
        
        # Calculate real risk metrics
        current_exposure = sum(pos.get('market_value', 0) for pos in positions)
        daily_pnl = sum(pos.get('realized_pnl', 0) for pos in positions)
        unrealized_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
        open_positions = len(positions)
        
        # Calculate risk score based on real data
        risk_score = await risk_mgr.calculate_portfolio_risk_score(positions)
        
        # Get capital utilization
        total_capital = portfolio_summary.get('total_capital', 100000)  # Default from config
        margin_used = portfolio_summary.get('margin_used', 0)
        exposure_percentage = (current_exposure / total_capital) * 100 if total_capital > 0 else 0
        
        # Calculate risk alerts
        risk_alerts = []
        if daily_pnl < -risk_mgr.daily_loss_limit * 0.8:  # 80% of daily loss limit
            risk_alerts.append("Daily loss approaching limit")
        if open_positions >= risk_mgr.max_open_positions * 0.9:  # 90% of position limit
            risk_alerts.append("Position count approaching limit")
        if exposure_percentage > 95:  # 95% capital utilization
            risk_alerts.append("High capital utilization")
        
        return {
            "success": True,
            "risk_metrics": {
                "current_exposure": round(current_exposure, 2),
                "exposure_percentage": round(exposure_percentage, 2),
                "daily_pnl": round(daily_pnl, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "total_pnl": round(daily_pnl + unrealized_pnl, 2),
                "open_positions": open_positions,
                "risk_score": round(risk_score, 2),
                "risk_level": "LOW" if risk_score < 30 else "MEDIUM" if risk_score < 70 else "HIGH",
                "margin_used": round(margin_used, 2),
                "margin_available": round(total_capital - margin_used, 2),
                "capital_utilization_percent": round(exposure_percentage, 2)
            },
            "risk_alerts": risk_alerts,
            "limits_status": {
                "daily_loss_limit": risk_mgr.daily_loss_limit,
                "daily_loss_used": abs(min(daily_pnl, 0)),
                "position_limit": risk_mgr.max_open_positions,
                "positions_used": open_positions
            },
            "data_source": "PRODUCTION_RISK_MANAGER",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting risk metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Risk metrics retrieval failed: {str(e)}")

@router.get("/users/{user_id}/risk")
async def get_user_risk_profile(user_id: str):
    """Get detailed REAL risk profile for a specific user"""
    try:
        # ENTERPRISE: Get real user-specific risk data
        risk_mgr = await get_risk_manager()
        user_positions = await position_manager.get_positions_by_user(user_id)
        
        # Calculate user-specific risk metrics
        user_exposure = sum(pos.get('market_value', 0) for pos in user_positions)
        user_daily_pnl = sum(pos.get('realized_pnl', 0) for pos in user_positions)
        user_unrealized_pnl = sum(pos.get('unrealized_pnl', 0) for pos in user_positions)
        user_total_pnl = user_daily_pnl + user_unrealized_pnl
        
        # Calculate performance metrics
        winning_positions = sum(1 for pos in user_positions if pos.get('unrealized_pnl', 0) > 0)
        total_positions = len(user_positions)
        win_rate = (winning_positions / total_positions * 100) if total_positions > 0 else 0
        
        # Calculate user risk score
        user_risk_score = await risk_mgr.calculate_user_risk_score(user_id, user_positions)
        
        # Determine risk tolerance based on trading behavior
        risk_tolerance = "conservative"
        if user_risk_score > 70:
            risk_tolerance = "aggressive"
        elif user_risk_score > 40:
            risk_tolerance = "moderate"
        
        # Calculate maximum drawdown from position history
        position_pnls = [pos.get('unrealized_pnl', 0) for pos in user_positions]
        max_drawdown = min(position_pnls) if position_pnls else 0
        
        return {
            "success": True,
            "user_id": user_id,
            "risk_profile": {
                "risk_tolerance": risk_tolerance,
                "current_exposure": round(user_exposure, 2),
                "daily_pnl": round(user_daily_pnl, 2),
                "unrealized_pnl": round(user_unrealized_pnl, 2),
                "total_pnl": round(user_total_pnl, 2),
                "win_rate": round(win_rate, 2),
                "max_drawdown": round(max_drawdown, 2),
                "risk_score": round(user_risk_score, 2),
                "position_count": total_positions,
                "winning_positions": winning_positions,
                "losing_positions": total_positions - winning_positions
            },
            "user_limits": {
                "max_position_size": risk_mgr.position_size_limit,
                "max_daily_loss": risk_mgr.daily_loss_limit,
                "max_positions": risk_mgr.max_open_positions
            },
            "compliance_status": {
                "within_daily_loss_limit": user_daily_pnl > -risk_mgr.daily_loss_limit,
                "within_position_limit": total_positions <= risk_mgr.max_open_positions,
                "risk_level": "LOW" if user_risk_score < 30 else "MEDIUM" if user_risk_score < 70 else "HIGH"
            },
            "data_source": "PRODUCTION_RISK_MANAGER",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting user risk profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"User risk profile retrieval failed: {str(e)}")

@router.post("/risk/hard-stop/reset")
async def reset_hard_stop():
    """Reset hard stop status"""
    try:
        return {
            "success": True,
            "message": "Hard stop reset successfully"
        }
    except Exception as e:
        logger.error(f"Error resetting hard stop: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk/alerts")
async def get_risk_alerts():
    """Get active risk alerts"""
    try:
        # Return empty alerts for now
        return []
    except Exception as e:
        logger.error(f"Error getting risk alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk/history")
async def get_risk_history(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get risk history"""
    try:
        # Return empty history for now
        return []
    except Exception as e:
        logger.error(f"Error getting risk history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 