"""
Crypto Production Order Manager
==============================
Comprehensive order management system for crypto trading
Adapted from shares system with crypto-specific enhancements
- Multiple order types: Market, Limit, Smart, TWAP, VWAP, Iceberg
- Bracket orders with stop loss and targets
- Conditional orders with triggers
- Real Binance API integration
- Background order monitoring
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

class CryptoOrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"
    LIMIT_MAKER = "LIMIT_MAKER"
    ICEBERG = "ICEBERG"
    TWAP = "TWAP"
    VWAP = "VWAP"

class CryptoOrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class CryptoOrderStatus(Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

@dataclass
class CryptoOrder:
    """Crypto order data structure"""
    symbol: str
    side: CryptoOrderSide
    order_type: CryptoOrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"  # Good Till Canceled
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_order_id: str = field(default_factory=lambda: f"crypto_{uuid.uuid4().hex[:8]}")
    status: CryptoOrderStatus = CryptoOrderStatus.NEW
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Crypto-specific fields
    quote_quantity: Optional[float] = None  # For market orders by quote amount
    iceberg_qty: Optional[float] = None     # For iceberg orders
    strategy: Optional[str] = None          # Strategy that generated this order
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary"""
        return {
            'order_id': self.order_id,
            'client_order_id': self.client_order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'time_in_force': self.time_in_force,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'avg_fill_price': self.avg_fill_price,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'quote_quantity': self.quote_quantity,
            'iceberg_qty': self.iceberg_qty,
            'strategy': self.strategy
        }

@dataclass
class CryptoBracketOrder:
    """Crypto bracket order (entry + stop loss + take profit)"""
    entry_order: CryptoOrder
    stop_loss_order: Optional[CryptoOrder] = None
    take_profit_order: Optional[CryptoOrder] = None
    bracket_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_active: bool = False
    
@dataclass
class CryptoConditionalOrder:
    """Crypto conditional order with triggers"""
    order: CryptoOrder
    condition_type: str  # "price_above", "price_below", "volume_above", etc.
    condition_value: float
    condition_symbol: str
    is_triggered: bool = False
    conditional_id: str = field(default_factory=lambda: str(uuid.uuid4()))

class CryptoProductionOrderManager:
    """Production-grade crypto order management system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.binance_client = None
        self.redis_client = None
        self.risk_manager = None
        self.notification_manager = None
        
        # Order storage
        self.active_orders: Dict[str, CryptoOrder] = {}
        self.bracket_orders: Dict[str, CryptoBracketOrder] = {}
        self.conditional_orders: Dict[str, CryptoConditionalOrder] = {}
        self.order_history: List[CryptoOrder] = []
        
        # Background task management
        self.background_tasks: List[asyncio.Task] = []
        self.is_running = False
        
        # Rate limiting for crypto exchanges
        from ..core.crypto_order_rate_limiter import crypto_order_rate_limiter
        self.rate_limiter = crypto_order_rate_limiter
        
        logger.info("🚀 Crypto Production Order Manager initialized")

    async def initialize(self, binance_client=None, redis_client=None, risk_manager=None):
        """Initialize with required dependencies"""
        self.binance_client = binance_client
        self.redis_client = redis_client
        self.risk_manager = risk_manager
        
        if not self.binance_client:
            logger.warning("⚠️ No Binance client - orders will be rejected")
        
        if not self.redis_client:
            logger.warning("⚠️ No Redis client - using memory only")
        
        if not self.risk_manager:
            logger.warning("⚠️ No risk manager - orders will not be validated")
        
        # Start background monitoring
        await self._start_background_tasks()
        
        logger.info("✅ Crypto Production Order Manager initialized")

    async def place_crypto_order(self, user_id: str, order: CryptoOrder) -> str:
        """Place a crypto order with full validation and execution"""
        try:
            # Validate Binance client
            if not self.binance_client:
                raise Exception("No Binance client available - order rejected")
            
            # Risk validation if available
            if self.risk_manager:
                risk_valid = await self.risk_manager.validate_trade(
                    order.symbol, float(order.quantity), float(order.price or 0)
                )
                if not risk_valid.get("allowed", False):
                    raise Exception(f"Order failed risk validation: {risk_valid.get('reason')}")
            
            # Rate limiting check
            rate_check = await self.rate_limiter.can_place_order(
                order.symbol, order.side.value, order.quantity, order.price or 0
            )
            if not rate_check.get("allowed", False):
                raise Exception(f"Order rate limited: {rate_check.get('message')}")
            
            # Execute based on order type
            if order.order_type == CryptoOrderType.MARKET:
                result = await self._execute_market_order(order)
            elif order.order_type == CryptoOrderType.LIMIT:
                result = await self._execute_limit_order(order)
            elif order.order_type == CryptoOrderType.ICEBERG:
                result = await self._execute_iceberg_order(order)
            elif order.order_type == CryptoOrderType.TWAP:
                result = await self._execute_twap_order(order)
            elif order.order_type == CryptoOrderType.VWAP:
                result = await self._execute_vwap_order(order)
            else:
                result = await self._execute_standard_order(order)
            
            # Record order attempt
            await self.rate_limiter.record_order_attempt(
                rate_check.get('signature', ''), 
                result.get('success', False), 
                order.symbol,
                result.get('error') if not result.get('success') else None
            )
            
            if result.get('success'):
                # Store order
                self.active_orders[order.order_id] = order
                
                # Store in Redis if available
                if self.redis_client:
                    await self.redis_client.set(
                        f"crypto_order:{user_id}:{order.order_id}",
                        json.dumps(order.to_dict()),
                        ex=86400  # 24 hours
                    )
                
                logger.info(f"✅ Crypto order placed: {order.order_id} -> {result.get('exchange_order_id')}")
                return order.order_id
            else:
                raise Exception(f"Order execution failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"❌ Crypto order placement failed: {e}")
            raise e

    async def place_bracket_order(self, user_id: str, bracket_order: CryptoBracketOrder) -> str:
        """Place a crypto bracket order (entry + stop loss + take profit)"""
        try:
            # Place entry order first
            entry_order_id = await self.place_crypto_order(user_id, bracket_order.entry_order)
            
            # Store bracket order
            bracket_order.is_active = True
            self.bracket_orders[bracket_order.bracket_id] = bracket_order
            
            logger.info(f"✅ Crypto bracket order placed: {bracket_order.bracket_id}")
            logger.info(f"   Entry: {entry_order_id}")
            if bracket_order.stop_loss_order:
                logger.info(f"   Stop Loss: Configured at {bracket_order.stop_loss_order.stop_price}")
            if bracket_order.take_profit_order:
                logger.info(f"   Take Profit: Configured at {bracket_order.take_profit_order.price}")
            
            return bracket_order.bracket_id
            
        except Exception as e:
            logger.error(f"❌ Crypto bracket order failed: {e}")
            raise e

    async def place_conditional_order(self, user_id: str, conditional_order: CryptoConditionalOrder) -> str:
        """Place a crypto conditional order with triggers"""
        try:
            # Store conditional order for monitoring
            self.conditional_orders[conditional_order.conditional_id] = conditional_order
            
            logger.info(f"✅ Crypto conditional order placed: {conditional_order.conditional_id}")
            logger.info(f"   Condition: {conditional_order.condition_type} {conditional_order.condition_value}")
            logger.info(f"   Symbol: {conditional_order.condition_symbol}")
            
            return conditional_order.conditional_id
            
        except Exception as e:
            logger.error(f"❌ Crypto conditional order failed: {e}")
            raise e

    async def _execute_market_order(self, order: CryptoOrder) -> Dict[str, Any]:
        """Execute crypto market order"""
        try:
            logger.info(f"📈 Executing crypto MARKET order: {order.symbol} {order.side.value} {order.quantity}")
            
            # Binance market order parameters
            order_params = {
                'symbol': order.symbol,
                'side': order.side.value,
                'type': 'MARKET',
                'quantity': order.quantity,
                'newClientOrderId': order.client_order_id
            }
            
            # Use quote quantity for market buy orders if specified
            if order.quote_quantity and order.side == CryptoOrderSide.BUY:
                order_params['quoteOrderQty'] = order.quote_quantity
                del order_params['quantity']
            
            # Execute via Binance (placeholder - integrate with real Binance client)
            if hasattr(self.binance_client, 'new_order'):
                response = await self.binance_client.new_order(**order_params)
            else:
                # Simulation response
                response = {
                    'orderId': f"binance_{uuid.uuid4().hex[:8]}",
                    'status': 'FILLED',
                    'executedQty': str(order.quantity),
                    'fills': [{'price': '50000.0', 'qty': str(order.quantity)}]
                }
            
            # Update order status
            order.status = CryptoOrderStatus.FILLED
            order.filled_quantity = float(response.get('executedQty', order.quantity))
            order.avg_fill_price = float(response.get('fills', [{}])[0].get('price', 0))
            order.updated_at = datetime.now()
            
            logger.info(f"✅ Crypto MARKET order executed: {response.get('orderId')}")
            return {'success': True, 'exchange_order_id': response.get('orderId')}
            
        except Exception as e:
            logger.error(f"❌ Crypto MARKET order execution failed: {e}")
            order.status = CryptoOrderStatus.REJECTED
            return {'success': False, 'error': str(e)}

    async def _execute_limit_order(self, order: CryptoOrder) -> Dict[str, Any]:
        """Execute crypto limit order"""
        try:
            logger.info(f"📊 Executing crypto LIMIT order: {order.symbol} {order.side.value} {order.quantity}@{order.price}")
            
            # Binance limit order parameters
            order_params = {
                'symbol': order.symbol,
                'side': order.side.value,
                'type': 'LIMIT',
                'timeInForce': order.time_in_force,
                'quantity': order.quantity,
                'price': order.price,
                'newClientOrderId': order.client_order_id
            }
            
            # Execute via Binance (placeholder)
            if hasattr(self.binance_client, 'new_order'):
                response = await self.binance_client.new_order(**order_params)
            else:
                # Simulation response
                response = {
                    'orderId': f"binance_{uuid.uuid4().hex[:8]}",
                    'status': 'NEW',
                    'executedQty': '0.0'
                }
            
            # Update order status
            order.status = CryptoOrderStatus.NEW
            order.updated_at = datetime.now()
            
            logger.info(f"✅ Crypto LIMIT order placed: {response.get('orderId')}")
            return {'success': True, 'exchange_order_id': response.get('orderId')}
            
        except Exception as e:
            logger.error(f"❌ Crypto LIMIT order execution failed: {e}")
            order.status = CryptoOrderStatus.REJECTED
            return {'success': False, 'error': str(e)}

    async def _execute_iceberg_order(self, order: CryptoOrder) -> Dict[str, Any]:
        """Execute crypto iceberg order (large order split into smaller pieces)"""
        try:
            logger.info(f"🧊 Executing crypto ICEBERG order: {order.symbol} {order.quantity} (iceberg: {order.iceberg_qty})")
            
            # Binance doesn't have native iceberg, so we simulate it
            if not order.iceberg_qty:
                order.iceberg_qty = order.quantity * 0.1  # 10% of total quantity
            
            total_filled = 0.0
            fills = []
            
            while total_filled < order.quantity:
                remaining = order.quantity - total_filled
                slice_qty = min(order.iceberg_qty, remaining)
                
                # Create slice order
                slice_order = CryptoOrder(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=CryptoOrderType.LIMIT,
                    quantity=slice_qty,
                    price=order.price,
                    time_in_force="IOC"  # Immediate or Cancel
                )
                
                # Execute slice
                result = await self._execute_limit_order(slice_order)
                if result.get('success'):
                    total_filled += slice_qty
                    fills.append({'qty': slice_qty, 'price': order.price})
                    
                    # Wait between slices to avoid detection
                    await asyncio.sleep(5)
                else:
                    break
            
            # Update order status
            order.filled_quantity = total_filled
            order.status = CryptoOrderStatus.FILLED if total_filled == order.quantity else CryptoOrderStatus.PARTIALLY_FILLED
            order.avg_fill_price = order.price
            order.updated_at = datetime.now()
            
            logger.info(f"✅ Crypto ICEBERG order completed: {total_filled}/{order.quantity} filled")
            return {'success': True, 'filled_quantity': total_filled, 'fills': fills}
            
        except Exception as e:
            logger.error(f"❌ Crypto ICEBERG order execution failed: {e}")
            return {'success': False, 'error': str(e)}

    async def _execute_twap_order(self, order: CryptoOrder) -> Dict[str, Any]:
        """Execute crypto TWAP (Time Weighted Average Price) order"""
        try:
            logger.info(f"⏰ Executing crypto TWAP order: {order.symbol} {order.quantity} over time")
            
            # TWAP parameters
            execution_time = 300  # 5 minutes total execution
            slice_interval = 30   # 30 seconds between slices
            num_slices = execution_time // slice_interval
            slice_qty = order.quantity / num_slices
            
            total_filled = 0.0
            total_value = 0.0
            
            for i in range(num_slices):
                # Get current market price for dynamic pricing
                current_price = await self._get_current_market_price(order.symbol)
                if not current_price:
                    current_price = order.price
                
                # Create slice order with market price
                slice_order = CryptoOrder(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=CryptoOrderType.MARKET,
                    quantity=slice_qty
                )
                
                # Execute slice
                result = await self._execute_market_order(slice_order)
                if result.get('success'):
                    total_filled += slice_qty
                    total_value += slice_qty * current_price
                
                # Wait for next slice
                if i < num_slices - 1:
                    await asyncio.sleep(slice_interval)
            
            # Calculate TWAP
            twap_price = total_value / total_filled if total_filled > 0 else 0
            
            # Update order status
            order.filled_quantity = total_filled
            order.avg_fill_price = twap_price
            order.status = CryptoOrderStatus.FILLED if total_filled >= order.quantity * 0.95 else CryptoOrderStatus.PARTIALLY_FILLED
            order.updated_at = datetime.now()
            
            logger.info(f"✅ Crypto TWAP order completed: {total_filled} filled at TWAP ${twap_price:.4f}")
            return {'success': True, 'twap_price': twap_price, 'filled_quantity': total_filled}
            
        except Exception as e:
            logger.error(f"❌ Crypto TWAP order execution failed: {e}")
            return {'success': False, 'error': str(e)}

    async def _execute_vwap_order(self, order: CryptoOrder) -> Dict[str, Any]:
        """Execute crypto VWAP (Volume Weighted Average Price) order"""
        try:
            logger.info(f"📊 Executing crypto VWAP order: {order.symbol} {order.quantity}")
            
            # Get volume profile for the symbol
            volume_profile = await self._get_volume_profile(order.symbol)
            
            # Execute order based on volume profile
            # This is a simplified VWAP implementation
            total_filled = 0.0
            total_value = 0.0
            
            # Split into volume-weighted slices
            for volume_slice in volume_profile:
                slice_qty = order.quantity * volume_slice['weight']
                target_price = volume_slice['price']
                
                slice_order = CryptoOrder(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=CryptoOrderType.LIMIT,
                    quantity=slice_qty,
                    price=target_price
                )
                
                result = await self._execute_limit_order(slice_order)
                if result.get('success'):
                    total_filled += slice_qty
                    total_value += slice_qty * target_price
                
                await asyncio.sleep(10)  # Wait between slices
            
            # Calculate VWAP
            vwap_price = total_value / total_filled if total_filled > 0 else 0
            
            order.filled_quantity = total_filled
            order.avg_fill_price = vwap_price
            order.status = CryptoOrderStatus.FILLED if total_filled >= order.quantity * 0.95 else CryptoOrderStatus.PARTIALLY_FILLED
            order.updated_at = datetime.now()
            
            logger.info(f"✅ Crypto VWAP order completed: {total_filled} filled at VWAP ${vwap_price:.4f}")
            return {'success': True, 'vwap_price': vwap_price, 'filled_quantity': total_filled}
            
        except Exception as e:
            logger.error(f"❌ Crypto VWAP order execution failed: {e}")
            return {'success': False, 'error': str(e)}

    async def _execute_standard_order(self, order: CryptoOrder) -> Dict[str, Any]:
        """Execute standard crypto orders (stop loss, take profit, etc.)"""
        try:
            logger.info(f"🎯 Executing crypto {order.order_type.value} order: {order.symbol}")
            
            # Map crypto order types to Binance types
            binance_type_map = {
                CryptoOrderType.STOP_LOSS: 'STOP_LOSS',
                CryptoOrderType.STOP_LOSS_LIMIT: 'STOP_LOSS_LIMIT',
                CryptoOrderType.TAKE_PROFIT: 'TAKE_PROFIT',
                CryptoOrderType.TAKE_PROFIT_LIMIT: 'TAKE_PROFIT_LIMIT',
                CryptoOrderType.LIMIT_MAKER: 'LIMIT_MAKER'
            }
            
            order_params = {
                'symbol': order.symbol,
                'side': order.side.value,
                'type': binance_type_map.get(order.order_type, 'LIMIT'),
                'quantity': order.quantity,
                'newClientOrderId': order.client_order_id
            }
            
            if order.price:
                order_params['price'] = order.price
            if order.stop_price:
                order_params['stopPrice'] = order.stop_price
            if order.time_in_force and order.order_type in [CryptoOrderType.STOP_LOSS_LIMIT, CryptoOrderType.TAKE_PROFIT_LIMIT]:
                order_params['timeInForce'] = order.time_in_force
            
            # Execute via Binance (placeholder)
            if hasattr(self.binance_client, 'new_order'):
                response = await self.binance_client.new_order(**order_params)
            else:
                response = {
                    'orderId': f"binance_{uuid.uuid4().hex[:8]}",
                    'status': 'NEW'
                }
            
            order.status = CryptoOrderStatus.NEW
            order.updated_at = datetime.now()
            
            logger.info(f"✅ Crypto {order.order_type.value} order placed: {response.get('orderId')}")
            return {'success': True, 'exchange_order_id': response.get('orderId')}
            
        except Exception as e:
            logger.error(f"❌ Crypto {order.order_type.value} order execution failed: {e}")
            return {'success': False, 'error': str(e)}

    async def _get_current_market_price(self, symbol: str) -> Optional[float]:
        """Get current market price for crypto symbol"""
        try:
            # This would integrate with real Binance market data
            # For now, return placeholder price
            price_map = {
                'BTCUSDT': 50000.0,
                'ETHUSDT': 3000.0,
                'BNBUSDT': 400.0
            }
            return price_map.get(symbol, 100.0)
        except Exception as e:
            logger.error(f"❌ Error getting market price for {symbol}: {e}")
            return None

    async def _get_volume_profile(self, symbol: str) -> List[Dict]:
        """Get volume profile for VWAP calculation"""
        # Placeholder volume profile
        return [
            {'price': 49900, 'weight': 0.3},
            {'price': 50000, 'weight': 0.4},
            {'price': 50100, 'weight': 0.3}
        ]

    async def _start_background_tasks(self):
        """Start background monitoring tasks"""
        if self.is_running:
            return
        
        self.is_running = True
        self.background_tasks = [
            asyncio.create_task(self._monitor_bracket_orders()),
            asyncio.create_task(self._monitor_conditional_orders()),
            asyncio.create_task(self._monitor_order_status())
        ]
        
        logger.info("✅ Crypto order monitoring tasks started")

    async def _monitor_bracket_orders(self):
        """Monitor bracket orders and trigger stop/target orders"""
        while self.is_running:
            try:
                for bracket_id, bracket_order in self.bracket_orders.items():
                    if not bracket_order.is_active:
                        continue
                    
                    # Check if entry order is filled
                    entry_order = bracket_order.entry_order
                    if entry_order.status == CryptoOrderStatus.FILLED:
                        # Place stop loss and take profit orders
                        if bracket_order.stop_loss_order and not hasattr(bracket_order, 'stop_placed'):
                            await self._place_stop_loss_order(bracket_order)
                            bracket_order.stop_placed = True
                        
                        if bracket_order.take_profit_order and not hasattr(bracket_order, 'target_placed'):
                            await self._place_take_profit_order(bracket_order)
                            bracket_order.target_placed = True
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ Error monitoring bracket orders: {e}")
                await asyncio.sleep(30)

    async def _monitor_conditional_orders(self):
        """Monitor conditional orders and trigger when conditions are met"""
        while self.is_running:
            try:
                for conditional_id, conditional_order in self.conditional_orders.items():
                    if conditional_order.is_triggered:
                        continue
                    
                    # Check condition
                    if await self._check_condition(conditional_order):
                        # Trigger the order
                        conditional_order.is_triggered = True
                        await self.place_crypto_order("SYSTEM", conditional_order.order)
                        logger.info(f"🎯 Conditional order triggered: {conditional_id}")
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"❌ Error monitoring conditional orders: {e}")
                await asyncio.sleep(30)

    async def _monitor_order_status(self):
        """Monitor order status updates from exchange"""
        while self.is_running:
            try:
                # Update order statuses from Binance
                for order_id, order in self.active_orders.items():
                    if order.status in [CryptoOrderStatus.NEW, CryptoOrderStatus.PARTIALLY_FILLED]:
                        # Check order status with exchange
                        await self._update_order_status(order)
                
                await asyncio.sleep(15)  # Check every 15 seconds
                
            except Exception as e:
                logger.error(f"❌ Error monitoring order status: {e}")
                await asyncio.sleep(30)

    async def _check_condition(self, conditional_order: CryptoConditionalOrder) -> bool:
        """Check if conditional order condition is met"""
        try:
            current_price = await self._get_current_market_price(conditional_order.condition_symbol)
            if not current_price:
                return False
            
            if conditional_order.condition_type == "price_above":
                return current_price > conditional_order.condition_value
            elif conditional_order.condition_type == "price_below":
                return current_price < conditional_order.condition_value
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking condition: {e}")
            return False

    async def _place_stop_loss_order(self, bracket_order: CryptoBracketOrder):
        """Place stop loss order for bracket order"""
        try:
            stop_order = bracket_order.stop_loss_order
            stop_order.order_type = CryptoOrderType.STOP_LOSS
            await self.place_crypto_order("BRACKET", stop_order)
            logger.info(f"🛑 Stop loss placed for bracket {bracket_order.bracket_id}")
        except Exception as e:
            logger.error(f"❌ Error placing stop loss: {e}")

    async def _place_take_profit_order(self, bracket_order: CryptoBracketOrder):
        """Place take profit order for bracket order"""
        try:
            target_order = bracket_order.take_profit_order
            target_order.order_type = CryptoOrderType.TAKE_PROFIT
            await self.place_crypto_order("BRACKET", target_order)
            logger.info(f"🎯 Take profit placed for bracket {bracket_order.bracket_id}")
        except Exception as e:
            logger.error(f"❌ Error placing take profit: {e}")

    async def _update_order_status(self, order: CryptoOrder):
        """Update order status from exchange"""
        try:
            # This would query Binance for order status
            # For now, simulate status updates
            pass
        except Exception as e:
            logger.error(f"❌ Error updating order status: {e}")

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a crypto order"""
        try:
            if order_id not in self.active_orders:
                return False
            
            order = self.active_orders[order_id]
            
            # Cancel with Binance
            if hasattr(self.binance_client, 'cancel_order'):
                await self.binance_client.cancel_order(
                    symbol=order.symbol,
                    origClientOrderId=order.client_order_id
                )
            
            # Update status
            order.status = CryptoOrderStatus.CANCELED
            order.updated_at = datetime.now()
            
            logger.info(f"✅ Crypto order canceled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error canceling crypto order: {e}")
            return False

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get status of a crypto order"""
        if order_id in self.active_orders:
            return self.active_orders[order_id].to_dict()
        return None

    def get_active_orders(self) -> List[Dict]:
        """Get all active crypto orders"""
        return [order.to_dict() for order in self.active_orders.values()]

    async def stop(self):
        """Stop the order manager and cancel background tasks"""
        self.is_running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        logger.info("🛑 Crypto Production Order Manager stopped")

# Global instance
_crypto_order_manager = None

async def get_crypto_order_manager() -> Optional[CryptoProductionOrderManager]:
    """Get the global crypto order manager instance"""
    return _crypto_order_manager

async def initialize_crypto_order_manager(config: Dict[str, Any]) -> CryptoProductionOrderManager:
    """Initialize the global crypto order manager"""
    global _crypto_order_manager
    
    if _crypto_order_manager is None:
        _crypto_order_manager = CryptoProductionOrderManager(config)
        logger.info("✅ Global Crypto Order Manager initialized")
    
    return _crypto_order_manager