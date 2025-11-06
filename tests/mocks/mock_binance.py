"""
Mock Binance Exchange for Testing

Simulates Binance API responses without real network calls.
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import random
from dataclasses import dataclass, field


@dataclass
class MockOrder:
    """Mock order"""
    symbol: str
    order_id: str
    client_order_id: str
    side: str  # 'BUY' or 'SELL'
    type: str  # 'LIMIT', 'MARKET'
    price: float
    quantity: float
    filled_quantity: float = 0.0
    status: str = 'NEW'  # NEW, PARTIALLY_FILLED, FILLED, CANCELLED
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MockBinanceExchange:
    """
    Mock Binance exchange for testing.
    
    Features:
    - Order placement and cancellation
    - Market data simulation
    - Order book generation
    - Trade execution simulation
    """
    
    def __init__(self, starting_balance: float = 100000.0):
        self.balances = {
            'USDT': starting_balance,
            'BTC': 0.0,
            'ETH': 0.0,
            'BNB': 0.0
        }
        
        self.orders: Dict[str, MockOrder] = {}
        self.trades: List[Dict] = []
        self.order_counter = 1000
        
        # Mock prices
        self.prices = {
            'BTCUSDT': 45000.0,
            'ETHUSDT': 3000.0,
            'BNBUSDT': 300.0
        }
        
        # Order book
        self.order_books: Dict[str, Dict] = {}
        
        print(f"MockBinanceExchange initialized with ${starting_balance:,.2f}")
    
    async def get_account(self) -> Dict:
        """Get account information"""
        return {
            'balances': [
                {'asset': asset, 'free': amount, 'locked': 0.0}
                for asset, amount in self.balances.items()
            ]
        }
    
    async def get_ticker_price(self, symbol: str) -> Dict:
        """Get current price"""
        if symbol not in self.prices:
            raise ValueError(f"Unknown symbol: {symbol}")
        
        # Add small random variation
        base_price = self.prices[symbol]
        variation = base_price * random.uniform(-0.001, 0.001)
        price = base_price + variation
        
        return {
            'symbol': symbol,
            'price': price
        }
    
    async def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book"""
        if symbol not in self.prices:
            raise ValueError(f"Unknown symbol: {symbol}")
        
        mid_price = self.prices[symbol]
        tick_size = mid_price * 0.0001  # 0.01% tick
        
        # Generate bids and asks
        bids = []
        asks = []
        
        for i in range(limit):
            bid_price = mid_price - (i + 1) * tick_size
            ask_price = mid_price + (i + 1) * tick_size
            
            bid_qty = random.uniform(0.1, 2.0)
            ask_qty = random.uniform(0.1, 2.0)
            
            bids.append([str(bid_price), str(bid_qty)])
            asks.append([str(ask_price), str(ask_qty)])
        
        return {
            'lastUpdateId': int(datetime.utcnow().timestamp() * 1000),
            'bids': bids,
            'asks': asks
        }
    
    async def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        **kwargs
    ) -> Dict:
        """Create an order"""
        if symbol not in self.prices:
            raise ValueError(f"Unknown symbol: {symbol}")
        
        # Generate order ID
        order_id = str(self.order_counter)
        self.order_counter += 1
        
        client_order_id = kwargs.get('newClientOrderId', f'test_{order_id}')
        
        # Execution price
        if order_type == 'MARKET':
            exec_price = self.prices[symbol]
        else:
            exec_price = price or self.prices[symbol]
        
        # Create order
        order = MockOrder(
            symbol=symbol,
            order_id=order_id,
            client_order_id=client_order_id,
            side=side,
            type=order_type,
            price=exec_price,
            quantity=quantity
        )
        
        # Check balance
        base_asset, quote_asset = self._parse_symbol(symbol)
        
        if side == 'BUY':
            required = quantity * exec_price
            if self.balances.get(quote_asset, 0) < required:
                raise ValueError(f"Insufficient {quote_asset} balance")
            
            # Deduct balance
            self.balances[quote_asset] -= required
        else:  # SELL
            if self.balances.get(base_asset, 0) < quantity:
                raise ValueError(f"Insufficient {base_asset} balance")
            
            # Deduct balance
            self.balances[base_asset] -= quantity
        
        # Simulate instant fill for MARKET orders
        if order_type == 'MARKET':
            order.status = 'FILLED'
            order.filled_quantity = quantity
            
            # Update balances
            if side == 'BUY':
                self.balances[base_asset] = self.balances.get(base_asset, 0) + quantity
            else:
                self.balances[quote_asset] = self.balances.get(quote_asset, 0) + (quantity * exec_price)
            
            # Record trade
            self.trades.append({
                'symbol': symbol,
                'id': len(self.trades) + 1,
                'orderId': order_id,
                'price': exec_price,
                'qty': quantity,
                'quoteQty': quantity * exec_price,
                'time': int(datetime.utcnow().timestamp() * 1000),
                'isBuyer': side == 'BUY',
                'isMaker': False
            })
        
        # Store order
        self.orders[order_id] = order
        
        return {
            'symbol': symbol,
            'orderId': int(order_id),
            'clientOrderId': client_order_id,
            'transactTime': int(datetime.utcnow().timestamp() * 1000),
            'price': str(exec_price),
            'origQty': str(quantity),
            'executedQty': str(order.filled_quantity),
            'status': order.status,
            'type': order_type,
            'side': side
        }
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """Cancel an order"""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")
        
        order = self.orders[order_id]
        
        if order.status in ['FILLED', 'CANCELLED']:
            raise ValueError(f"Cannot cancel order in {order.status} status")
        
        # Refund balance
        base_asset, quote_asset = self._parse_symbol(symbol)
        
        if order.side == 'BUY':
            refund = (order.quantity - order.filled_quantity) * order.price
            self.balances[quote_asset] += refund
        else:
            refund = order.quantity - order.filled_quantity
            self.balances[base_asset] += refund
        
        order.status = 'CANCELLED'
        
        return {
            'symbol': symbol,
            'orderId': int(order_id),
            'status': 'CANCELLED'
        }
    
    async def get_order(self, symbol: str, order_id: str) -> Dict:
        """Get order status"""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")
        
        order = self.orders[order_id]
        
        return {
            'symbol': symbol,
            'orderId': int(order_id),
            'clientOrderId': order.client_order_id,
            'price': str(order.price),
            'origQty': str(order.quantity),
            'executedQty': str(order.filled_quantity),
            'status': order.status,
            'type': order.type,
            'side': order.side,
            'time': int(order.timestamp.timestamp() * 1000)
        }
    
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades"""
        symbol_trades = [t for t in self.trades if t['symbol'] == symbol]
        return symbol_trades[-limit:]
    
    def _parse_symbol(self, symbol: str) -> tuple:
        """Parse symbol into base and quote assets"""
        if symbol.endswith('USDT'):
            return symbol[:-4], 'USDT'
        elif symbol.endswith('BUSD'):
            return symbol[:-4], 'BUSD'
        else:
            raise ValueError(f"Cannot parse symbol: {symbol}")
    
    async def simulate_price_movement(self, symbol: str, pct_change: float):
        """Simulate price movement for testing"""
        if symbol in self.prices:
            self.prices[symbol] *= (1 + pct_change)
    
    def get_balance(self, asset: str) -> float:
        """Get asset balance"""
        return self.balances.get(asset, 0.0)
    
    def reset(self, starting_balance: float = 100000.0):
        """Reset exchange state"""
        self.balances = {
            'USDT': starting_balance,
            'BTC': 0.0,
            'ETH': 0.0,
            'BNB': 0.0
        }
        self.orders.clear()
        self.trades.clear()
        self.order_counter = 1000
        print(f"MockBinanceExchange reset with ${starting_balance:,.2f}")


