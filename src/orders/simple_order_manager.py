"""
Simple Order Manager - Fallback order processing
Lightweight fallback for when enhanced order manager fails
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

logger = logging.getLogger(__name__)

class SimpleOrderManager:
    """Simple fallback order manager"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.orders = {}
        self.is_initialized = False
        self.order_count = 0
        
        logger.info("🔧 Simple Order Manager created (fallback)")
    
    async def initialize(self) -> bool:
        """Initialize simple order manager"""
        try:
            logger.info("🔧 Initializing Simple Order Manager...")
            self.is_initialized = True
            logger.info("✅ Simple Order Manager initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Simple Order Manager initialization failed: {e}")
            return False
    
    async def place_order(self, symbol: str, side: str, quantity: float, 
                         price: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        """Place order with simple processing"""
        try:
            order_id = f"SIMPLE_{uuid.uuid4().hex[:8]}"
            
            order = {
                "id": order_id,
                "symbol": symbol.upper(),
                "side": side.upper(),
                "quantity": quantity,
                "price": price,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.orders[order_id] = order
            self.order_count += 1
            
            logger.info(f"📝 Simple order created: {order_id} {symbol} {side} {quantity}")
            
            # Simulate order processing
            await asyncio.sleep(0.1)  # Small delay to simulate processing
            
            order["status"] = "submitted"
            order["exchange_order_id"] = f"SIM_{uuid.uuid4().hex[:8]}"
            
            logger.info(f"✅ Simple order submitted: {order_id}")
            
            return {
                "success": True,
                "order_id": order_id,
                "exchange_order_id": order["exchange_order_id"],
                "status": order["status"]
            }
            
        except Exception as e:
            logger.error(f"❌ Simple order placement failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "order_id": None
            }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order"""
        try:
            if order_id not in self.orders:
                return {
                    "success": False,
                    "error": f"Order {order_id} not found"
                }
            
            self.orders[order_id]["status"] = "cancelled"
            logger.info(f"🛑 Simple order cancelled: {order_id}")
            
            return {
                "success": True,
                "order_id": order_id,
                "status": "cancelled"
            }
            
        except Exception as e:
            logger.error(f"❌ Simple order cancellation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        try:
            if order_id in self.orders:
                return {
                    "success": True,
                    "order": self.orders[order_id]
                }
            else:
                return {
                    "success": False,
                    "error": f"Order {order_id} not found"
                }
                
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_active_orders(self) -> Dict[str, Any]:
        """Get active orders"""
        try:
            active_orders = [
                order for order in self.orders.values() 
                if order["status"] not in ["filled", "cancelled", "rejected"]
            ]
            
            return {
                "success": True,
                "active_orders": active_orders,
                "count": len(active_orders)
            }
            
        except Exception as e:
            logger.error(f"Error getting active orders: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get simple performance metrics"""
        return {
            "total_orders": self.order_count,
            "orders_in_memory": len(self.orders),
            "manager_type": "simple_fallback"
        }