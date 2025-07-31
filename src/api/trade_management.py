from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

# Database imports
try:
    from sqlalchemy.orm import Session
    from src.config.database import get_db
    from src.models.trading_models import Trade, Position, Order, User
    from src.core.position_tracker import ProductionPositionTracker
    DATABASE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Database not available: {e}")
    DATABASE_AVAILABLE = False

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize position tracker
position_tracker = ProductionPositionTracker()

@router.get("/")
async def get_all_trades(
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    db: Session = Depends(get_db) if DATABASE_AVAILABLE else None
) -> List[Dict[str, Any]]:
    """Get all trades with real data"""
    try:
        if not DATABASE_AVAILABLE or not db:
            # Return in-memory trades if database not available
            trades = []
            if hasattr(position_tracker, 'trade_history'):
                trades = list(position_tracker.trade_history)
            
            logger.info(f"Retrieved {len(trades)} trades from memory")
            return trades
        
        # Get trades from database
        try:
            trades_query = db.query(Trade).offset(offset).limit(limit).all()
            trades_data = []
            
            for trade in trades_query:
                trade_dict = {
                    "trade_id": getattr(trade, 'trade_id', f"trade_{trade.id}"),
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": float(trade.quantity),
                    "price": float(trade.price),
                    "timestamp": trade.timestamp.isoformat() if trade.timestamp else datetime.utcnow().isoformat(),
                    "status": getattr(trade, 'status', 'completed'),
                    "strategy": getattr(trade, 'strategy_name', 'unknown'),
                    "pnl": float(getattr(trade, 'pnl', 0)),
                    "fees": float(getattr(trade, 'fees', 0))
                }
                trades_data.append(trade_dict)
            
            logger.info(f"Retrieved {len(trades_data)} trades from database")
            return trades_data
            
        except Exception as db_error:
            logger.warning(f"Database query failed: {db_error}")
            # Fallback to in-memory trades
            return []
        
    except Exception as e:
        logger.error(f"Error getting trades: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve trades: {str(e)}")

@router.get("/live")
async def get_live_trades(
    db: Session = Depends(get_db) if DATABASE_AVAILABLE else None
):
    """Get live trades data"""
    try:
        # Get recent trades (last 24 hours)
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        
        if DATABASE_AVAILABLE and db:
            try:
                recent_trades = db.query(Trade).filter(
                    Trade.timestamp >= recent_cutoff
                ).order_by(Trade.timestamp.desc()).limit(50).all()
                
                live_trades = []
                for trade in recent_trades:
                    live_trades.append({
                        "trade_id": getattr(trade, 'trade_id', f"trade_{trade.id}"),
                        "symbol": trade.symbol,
                        "side": trade.side,
                        "quantity": float(trade.quantity),
                        "price": float(trade.price),
                        "timestamp": trade.timestamp.isoformat(),
                        "status": getattr(trade, 'status', 'completed'),
                        "pnl": float(getattr(trade, 'pnl', 0))
                    })
                
                return {
                    "status": "success",
                    "trades": live_trades,
                    "count": len(live_trades),
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as db_error:
                logger.warning(f"Database error for live trades: {db_error}")
        
        # Fallback to position tracker data
        live_trades = []
        if hasattr(position_tracker, 'recent_trades'):
            live_trades = [
                trade for trade in position_tracker.recent_trades 
                if datetime.fromisoformat(trade.get('timestamp', '')) >= recent_cutoff
            ]
        
        return {
            "status": "success",
            "trades": live_trades,
            "count": len(live_trades),
            "message": "Live trades from position tracker",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting live trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_trade_statistics(
    days: Optional[int] = 30,
    db: Session = Depends(get_db) if DATABASE_AVAILABLE else None
):
    """Get trading statistics"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "total_volume": 0.0,
            "win_rate": 0.0,
            "average_trade_size": 0.0,
            "period_days": days,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if DATABASE_AVAILABLE and db:
            try:
                trades = db.query(Trade).filter(Trade.timestamp >= start_date).all()
                
                for trade in trades:
                    stats["total_trades"] += 1
                    pnl = float(getattr(trade, 'pnl', 0))
                    stats["total_pnl"] += pnl
                    stats["total_volume"] += float(trade.quantity) * float(trade.price)
                    
                    if pnl > 0:
                        stats["winning_trades"] += 1
                    elif pnl < 0:
                        stats["losing_trades"] += 1
                
                if stats["total_trades"] > 0:
                    stats["win_rate"] = stats["winning_trades"] / stats["total_trades"]
                    stats["average_trade_size"] = stats["total_volume"] / stats["total_trades"]
                
            except Exception as db_error:
                logger.warning(f"Database error for statistics: {db_error}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting trade statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_trading_performance(
    db: Session = Depends(get_db) if DATABASE_AVAILABLE else None
):
    """Get trading performance metrics"""
    try:
        performance = {
            "daily_pnl": 0.0,
            "weekly_pnl": 0.0,
            "monthly_pnl": 0.0,
            "total_pnl": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "trade_count": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Get performance from position tracker
        if hasattr(position_tracker, 'get_performance_summary'):
            try:
                tracker_performance = await position_tracker.get_performance_summary()
                performance.update(tracker_performance)
            except Exception as tracker_error:
                logger.warning(f"Position tracker performance error: {tracker_error}")
        
        return performance
        
    except Exception as e:
        logger.error(f"Error getting trading performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def trade_management_health():
    """Trade management system health check"""
    return {
        "status": "healthy",
        "service": "trade_management", 
        "database_available": DATABASE_AVAILABLE,
        "position_tracker_active": hasattr(position_tracker, 'is_initialized'),
        "timestamp": datetime.utcnow().isoformat()
    } 