"""
Enhanced Order Manager - Production-grade order processing
Based on working shares trading system with crypto adaptations
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    ICEBERG = "iceberg"

class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"

@dataclass
class Order:
    """Order data structure"""
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    fees: float = 0.0
    created_at: datetime = None
    updated_at: datetime = None
    exchange_order_id: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

class EnhancedOrderManager:
    """Production-grade order manager for crypto trading"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.orders: Dict[str, Order] = {}
        self.active_orders: Dict[str, Order] = {}
        self.completed_orders: Dict[str, Order] = {}
        self.is_initialized = False
        
        # Performance metrics
        self.total_orders = 0
        self.successful_orders = 0
        self.failed_orders = 0
        self.total_volume = 0.0
        self.total_fees = 0.0
        
        # Risk limits
        self.max_order_size = self.config.get('max_order_size', 1000000)
        self.max_daily_orders = self.config.get('max_daily_orders', 1000)
        self.daily_order_count = 0
        self.last_reset_date = datetime.utcnow().date()
        
        logger.info("🔧 Enhanced Order Manager created")
    
    async def initialize(self) -> bool:
        """Initialize order manager"""
        try:
            logger.info("🔧 Initializing Enhanced Order Manager...")
            
            # Initialize exchange connections
            await self._initialize_exchange_connections()
            
            # Start background tasks
            asyncio.create_task(self._order_monitoring_loop())
            asyncio.create_task(self._order_status_updater())
            
            self.is_initialized = True
            logger.info("✅ Enhanced Order Manager initialized")
            logger.info(f"📊 Max Order Size: ${self.max_order_size:,.2f}")
            logger.info(f"📊 Max Daily Orders: {self.max_daily_orders}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Enhanced Order Manager initialization failed: {e}")
            return False
    
    async def _initialize_exchange_connections(self):
        """Initialize connections to crypto exchanges"""
        try:
            # Initialize Binance connection
            logger.info("🔗 Initializing exchange connections...")
            
            # Here we would initialize actual exchange clients
            # For now, just log that we're ready for integration
            logger.info("✅ Exchange connections ready for integration")
            
        except Exception as e:
            logger.error(f"❌ Exchange connection initialization failed: {e}")
    
    async def place_order(self, symbol: str, side: str, quantity: float, 
                         price: Optional[float] = None, order_type: str = "market",
                         **kwargs) -> Dict[str, Any]:
        """Place a new trading order"""
        try:
            # Reset daily counter if needed
            self._reset_daily_counters_if_needed()
            
            # Validate order
            validation_result = await self._validate_order(symbol, side, quantity, price, order_type)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["reason"],
                    "order_id": None
                }
            
            # Create order
            order = Order(
                id=f"ORD_{uuid.uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}",
                symbol=symbol.upper(),
                side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
                type=OrderType.MARKET if order_type.upper() == "MARKET" else OrderType.LIMIT,
                quantity=quantity,
                price=price,
                status=OrderStatus.PENDING
            )
            
            # Store order
            self.orders[order.id] = order
            self.active_orders[order.id] = order
            self.total_orders += 1
            self.daily_order_count += 1
            
            logger.info(f"📝 Order created: {order.id} {symbol} {side} {quantity}@{price or 'market'}")
            
            # Submit order to exchange
            submission_result = await self._submit_order_to_exchange(order)
            
            if submission_result["success"]:
                order.status = OrderStatus.SUBMITTED
                order.exchange_order_id = submission_result.get("exchange_order_id")
                order.updated_at = datetime.utcnow()
                
                logger.info(f"✅ Order submitted: {order.id} → Exchange ID: {order.exchange_order_id}")
                
                return {
                    "success": True,
                    "order_id": order.id,
                    "exchange_order_id": order.exchange_order_id,
                    "status": order.status.value
                }
            else:
                order.status = OrderStatus.REJECTED
                order.error_message = submission_result.get("error", "Unknown error")
                order.updated_at = datetime.utcnow()
                
                # Move to completed orders
                if order.id in self.active_orders:
                    del self.active_orders[order.id]
                self.completed_orders[order.id] = order
                self.failed_orders += 1
                
                logger.error(f"❌ Order rejected: {order.id} - {order.error_message}")
                
                return {
                    "success": False,
                    "error": order.error_message,
                    "order_id": order.id
                }
                
        except Exception as e:
            logger.error(f"❌ Order placement failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "order_id": None
            }
    
    async def _validate_order(self, symbol: str, side: str, quantity: float, 
                             price: Optional[float], order_type: str) -> Dict[str, Any]:
        """Validate order parameters"""
        try:
            # Check daily order limit
            if self.daily_order_count >= self.max_daily_orders:
                return {
                    "valid": False,
                    "reason": f"Daily order limit exceeded ({self.max_daily_orders})"
                }
            
            # Check order size limit
            estimated_value = quantity * (price or 50000)  # Estimate with $50k if market order
            if estimated_value > self.max_order_size:
                return {
                    "valid": False,
                    "reason": f"Order size ${estimated_value:,.2f} exceeds limit ${self.max_order_size:,.2f}"
                }
            
            # Validate symbol format
            if not symbol or len(symbol) < 3:
                return {
                    "valid": False,
                    "reason": "Invalid symbol format"
                }
            
            # Validate quantity
            if quantity <= 0:
                return {
                    "valid": False,
                    "reason": "Quantity must be positive"
                }
            
            # Validate price for limit orders
            if order_type.upper() == "LIMIT" and (not price or price <= 0):
                return {
                    "valid": False,
                    "reason": "Limit orders require positive price"
                }
            
            return {"valid": True, "reason": "Order validation passed"}
            
        except Exception as e:
            logger.error(f"Order validation error: {e}")
            return {
                "valid": False,
                "reason": f"Validation error: {e}"
            }
    
    async def _submit_order_to_exchange(self, order: Order) -> Dict[str, Any]:
        """Submit order to crypto exchange"""
        try:
            # This would integrate with actual exchange APIs (Binance, etc.)
            # For now, simulate the submission
            
            logger.info(f"🔗 Submitting order to exchange: {order.symbol} {order.side.value} {order.quantity}")
            
            # Simulate exchange response
            exchange_order_id = f"BINANCE_{uuid.uuid4().hex[:12]}"
            
            # In real implementation, this would be:
            # result = await binance_client.create_order(
            #     symbol=order.symbol,
            #     side=order.side.value.upper(),
            #     type=order.type.value.upper(),
            #     quantity=order.quantity,
            #     price=order.price
            # )
            
            return {
                "success": True,
                "exchange_order_id": exchange_order_id,
                "message": "Order submitted to exchange"
            }
            
        except Exception as e:
            logger.error(f"Exchange submission error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an active order"""
        try:
            if order_id not in self.active_orders:
                return {
                    "success": False,
                    "error": f"Order {order_id} not found or not active"
                }
            
            order = self.active_orders[order_id]
            
            # Cancel on exchange
            cancellation_result = await self._cancel_order_on_exchange(order)
            
            if cancellation_result["success"]:
                order.status = OrderStatus.CANCELLED
                order.updated_at = datetime.utcnow()
                
                # Move to completed orders
                del self.active_orders[order_id]
                self.completed_orders[order_id] = order
                
                logger.info(f"✅ Order cancelled: {order_id}")
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "status": order.status.value
                }
            else:
                return {
                    "success": False,
                    "error": cancellation_result.get("error", "Cancellation failed")
                }
                
        except Exception as e:
            logger.error(f"Order cancellation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _cancel_order_on_exchange(self, order: Order) -> Dict[str, Any]:
        """Cancel order on exchange"""
        try:
            # This would integrate with actual exchange APIs
            logger.info(f"🔗 Cancelling order on exchange: {order.exchange_order_id}")
            
            # In real implementation:
            # result = await binance_client.cancel_order(
            #     symbol=order.symbol,
            #     orderId=order.exchange_order_id
            # )
            
            return {
                "success": True,
                "message": "Order cancelled on exchange"
            }
            
        except Exception as e:
            logger.error(f"Exchange cancellation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of a specific order"""
        try:
            if order_id in self.orders:
                order = self.orders[order_id]
                return {
                    "success": True,
                    "order": {
                        "id": order.id,
                        "symbol": order.symbol,
                        "side": order.side.value,
                        "type": order.type.value,
                        "quantity": order.quantity,
                        "price": order.price,
                        "status": order.status.value,
                        "filled_quantity": order.filled_quantity,
                        "avg_fill_price": order.avg_fill_price,
                        "fees": order.fees,
                        "created_at": order.created_at.isoformat(),
                        "updated_at": order.updated_at.isoformat(),
                        "exchange_order_id": order.exchange_order_id
                    }
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
        """Get all active orders"""
        try:
            active_orders_data = []
            for order in self.active_orders.values():
                active_orders_data.append({
                    "id": order.id,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "type": order.type.value,
                    "quantity": order.quantity,
                    "price": order.price,
                    "status": order.status.value,
                    "filled_quantity": order.filled_quantity,
                    "created_at": order.created_at.isoformat()
                })
            
            return {
                "success": True,
                "active_orders": active_orders_data,
                "count": len(active_orders_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting active orders: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _order_monitoring_loop(self):
        """Background loop to monitor order status"""
        logger.info("🔄 Starting order monitoring loop...")
        
        while self.is_initialized:
            try:
                # Check status of active orders
                for order_id in list(self.active_orders.keys()):
                    await self._update_order_status(order_id)
                
                await asyncio.sleep(5.0)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in order monitoring loop: {e}")
                await asyncio.sleep(10.0)
    
    async def _order_status_updater(self):
        """Background loop to update order statuses from exchange"""
        logger.info("📊 Starting order status updater...")
        
        while self.is_initialized:
            try:
                # Update order statuses from exchange
                await self._sync_orders_with_exchange()
                
                await asyncio.sleep(10.0)  # Sync every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in order status updater: {e}")
                await asyncio.sleep(15.0)
    
    async def _update_order_status(self, order_id: str):
        """Update status of a specific order"""
        try:
            if order_id not in self.active_orders:
                return
            
            order = self.active_orders[order_id]
            
            # Query exchange for order status
            # This would integrate with actual exchange APIs
            # For now, simulate status updates
            
            # Simulate order completion after some time
            time_since_creation = (datetime.utcnow() - order.created_at).total_seconds()
            if time_since_creation > 30:  # Simulate fill after 30 seconds
                order.status = OrderStatus.FILLED
                order.filled_quantity = order.quantity
                order.avg_fill_price = order.price or 50000  # Simulate fill price
                order.fees = order.quantity * order.avg_fill_price * 0.001  # 0.1% fee
                order.updated_at = datetime.utcnow()
                
                # Move to completed orders
                del self.active_orders[order_id]
                self.completed_orders[order_id] = order
                self.successful_orders += 1
                self.total_volume += order.quantity * order.avg_fill_price
                self.total_fees += order.fees
                
                logger.info(f"✅ Order filled: {order_id} at ${order.avg_fill_price:,.2f}")
            
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
    
    async def _sync_orders_with_exchange(self):
        """Sync order statuses with exchange"""
        try:
            # This would query the exchange for all order statuses
            # and update our local order tracking
            pass
            
        except Exception as e:
            logger.error(f"Error syncing orders with exchange: {e}")
    
    def _reset_daily_counters_if_needed(self):
        """Reset daily counters if new day"""
        current_date = datetime.utcnow().date()
        if current_date > self.last_reset_date:
            self.daily_order_count = 0
            self.last_reset_date = current_date
            logger.info("📅 Daily counters reset")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get order manager performance metrics"""
        try:
            success_rate = (self.successful_orders / max(self.total_orders, 1)) * 100
            
            return {
                "total_orders": self.total_orders,
                "successful_orders": self.successful_orders,
                "failed_orders": self.failed_orders,
                "success_rate": success_rate,
                "active_orders_count": len(self.active_orders),
                "completed_orders_count": len(self.completed_orders),
                "total_volume": self.total_volume,
                "total_fees": self.total_fees,
                "daily_order_count": self.daily_order_count,
                "avg_order_value": self.total_volume / max(self.total_orders, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}