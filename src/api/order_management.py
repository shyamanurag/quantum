from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

# Import PRODUCTION order manager (enterprise-grade)
from src.orders.crypto_production_order_manager import initialize_crypto_order_manager
from src.core.crypto_order_rate_limiter import crypto_order_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Global production order manager instance
production_order_manager = None

async def get_production_order_manager():
    """Get or initialize production order manager"""
    global production_order_manager
    if production_order_manager is None:
        production_order_manager = await initialize_crypto_order_manager({})
    return production_order_manager

@router.post("/")
async def create_order(order_data: Dict[str, Any]):
    """Create a new order using PRODUCTION order manager"""
    try:
        # ENTERPRISE: Get production order manager
        order_manager = await get_production_order_manager()
        
        # Validate required fields
        required_fields = ['symbol', 'action', 'quantity', 'order_type']
        missing_fields = [field for field in required_fields if field not in order_data]
        if missing_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        # ENTERPRISE: Check rate limits before creating order
        rate_check = await crypto_order_rate_limiter.can_place_order(
            order_data['symbol'],
            order_data['action'],
            order_data['quantity'],
            order_data.get('price', 0)
        )
        
        if not rate_check.get('allowed', False):
            raise HTTPException(
                status_code=429,
                detail=f"Order rate limit exceeded: {rate_check.get('message')}"
            )
        
        # Create crypto order from request data
        from src.orders.crypto_production_order_manager import CryptoOrder
        crypto_order = CryptoOrder(
            symbol=order_data['symbol'],
            action=order_data['action'],
            quantity=order_data['quantity'],
            order_type=order_data['order_type'],
            price=order_data.get('price'),
            user_id=order_data.get('user_id', 'SYSTEM'),
            metadata=order_data.get('metadata', {})
        )
        
        # ENTERPRISE: Execute order through production manager
        order_id = await order_manager.place_crypto_order("API_USER", crypto_order)
        
        # Record successful order attempt
        await crypto_order_rate_limiter.record_order_attempt(
            rate_check.get('signature', ''), True, order_data['symbol']
        )
        
        return {
            "success": True,
            "order_id": order_id,
            "message": "Order placed successfully via production order manager",
            "order_details": {
                "symbol": crypto_order.symbol,
                "action": crypto_order.action,
                "quantity": crypto_order.quantity,
                "order_type": crypto_order.order_type,
                "price": crypto_order.price
            },
            "data_source": "PRODUCTION_ORDER_MANAGER",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Record failed order attempt
        if 'rate_check' in locals() and rate_check.get('signature'):
            await crypto_order_rate_limiter.record_order_attempt(
                rate_check['signature'], False, order_data.get('symbol', ''), str(e)
            )
        
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Order creation failed: {str(e)}")

@router.get("/{order_id}")
async def get_order(order_id: str):
    """Get order details from production order manager"""
    try:
        # ENTERPRISE: Get production order manager
        order_manager = await get_production_order_manager()
        
        # Get order from production manager
        order_details = await order_manager.get_order_status(order_id)
        
        if not order_details:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        
        return {
            "success": True,
            "order_id": order_id,
            "order_details": order_details,
            "data_source": "PRODUCTION_ORDER_MANAGER",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Order retrieval failed: {str(e)}")

@router.put("/{order_id}")
async def update_order(order_id: str, order_update: Dict[str, Any]):
    """Update order details"""
    try:
        # Order not found since we're not persisting yet
        raise HTTPException(status_code=404, detail="Order not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an order using production order manager"""
    try:
        # ENTERPRISE: Get production order manager
        order_manager = await get_production_order_manager()
        
        # Get order details first to ensure it exists
        order_details = await order_manager.get_order_status(order_id)
        if not order_details:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        
        # Check if order can be cancelled
        current_status = order_details.get('status', '')
        if current_status in ['FILLED', 'CANCELLED', 'REJECTED']:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel order with status: {current_status}"
            )
        
        # ENTERPRISE: Cancel order through production manager
        cancellation_result = await order_manager.cancel_order(order_id)
        
        return {
            "success": True,
            "order_id": order_id,
            "cancellation_result": cancellation_result,
            "message": f"Order {order_id} cancellation requested",
            "data_source": "PRODUCTION_ORDER_MANAGER",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Order cancellation failed: {str(e)}")

@router.get("/users/{user_id}")
async def get_user_orders(user_id: str, status: Optional[str] = None):
    """Get all orders for a user"""
    try:
        return {
            "success": True,
            "user_id": user_id,
            "orders": [],
            "message": "No orders found"
        }
    except Exception as e:
        logger.error(f"Error getting user orders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/live")
async def get_live_orders():
    """Get all live orders from production order manager"""
    try:
        # ENTERPRISE: Get production order manager
        order_manager = await get_production_order_manager()
        
        # Get live orders (pending, submitted, partially filled)
        live_orders = await order_manager.get_live_orders()
        
        # Calculate live order metrics
        total_live = len(live_orders)
        pending_orders = sum(1 for order in live_orders if order.get('status') == 'PENDING')
        submitted_orders = sum(1 for order in live_orders if order.get('status') == 'SUBMITTED')
        
        return {
            "success": True,
            "orders": live_orders,
            "live_order_metrics": {
                "total_live_orders": total_live,
                "pending_orders": pending_orders,
                "submitted_orders": submitted_orders,
                "partially_filled": total_live - pending_orders - submitted_orders
            },
            "data_source": "PRODUCTION_ORDER_MANAGER",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting live orders: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Live orders retrieval failed: {str(e)}")

@router.get("/")
async def get_all_orders():
    """Get all orders"""
    try:
        return {
            "success": True,
            "orders": [],
            "message": "No orders found"
        }
    except Exception as e:
        logger.error(f"Error getting orders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 