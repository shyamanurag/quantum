"""
Trading Models - Orders, Trades, Positions
"""
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid
import enum

Base = declarative_base()


class OrderStatus(enum.Enum):
    """Order status enumeration"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderSide(enum.Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"


class OrderType(enum.Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LOSS_LIMIT = "stop_loss_limit"
    TAKE_PROFIT = "take_profit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


class Order(Base):
    """Order model"""
    __tablename__ = 'orders'
    
    order_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exchange_order_id = Column(String(100), unique=True, nullable=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING, index=True)
    
    # Quantities
    quantity = Column(Float, nullable=False)
    filled_quantity = Column(Float, default=0.0)
    remaining_quantity = Column(Float, nullable=False)
    
    # Prices
    price = Column(Float, nullable=True)  # Null for market orders
    average_fill_price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)
    
    # Strategy info
    strategy_id = Column(String(36), ForeignKey('strategies.strategy_id'), nullable=True, index=True)
    signal_id = Column(String(36), ForeignKey('signals.signal_id'), nullable=True)
    
    # Execution
    time_in_force = Column(String(10), default='GTC')  # GTC, IOC, FOK
    client_order_id = Column(String(100), unique=True, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    submitted_at = Column(DateTime, nullable=True)
    filled_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Fees
    commission = Column(Float, default=0.0)
    commission_asset = Column(String(10), nullable=True)
    
    # Relationships
    trades = relationship("Trade", back_populates="order")
    strategy = relationship("Strategy", back_populates="orders")
    
    def __repr__(self):
        return f"<Order(symbol='{self.symbol}', side='{self.side}', status='{self.status}')>"


class Trade(Base):
    """Trade model - individual fills"""
    __tablename__ = 'trades'
    
    trade_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exchange_trade_id = Column(String(100), unique=True, nullable=True, index=True)
    order_id = Column(String(36), ForeignKey('orders.order_id'), nullable=False, index=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    quote_quantity = Column(Float, nullable=False)  # price * quantity
    
    commission = Column(Float, default=0.0)
    commission_asset = Column(String(10), nullable=True)
    
    is_maker = Column(Boolean, default=False)
    
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="trades")
    
    def __repr__(self):
        return f"<Trade(symbol='{self.symbol}', price={self.price}, quantity={self.quantity})>"


class Position(Base):
    """Position model - current holdings"""
    __tablename__ = 'positions'
    
    position_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String(20), nullable=False, unique=True, index=True)
    
    # Position details
    side = Column(String(10), nullable=False)  # LONG, SHORT
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    
    # P&L
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    
    # Risk
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    trailing_stop = Column(Float, nullable=True)
    
    # Strategy
    strategy_id = Column(String(36), ForeignKey('strategies.strategy_id'), nullable=True, index=True)
    
    # Status
    is_open = Column(Boolean, default=True, index=True)
    
    # Timestamps
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    closed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="positions")
    
    def __repr__(self):
        return f"<Position(symbol='{self.symbol}', side='{self.side}', quantity={self.quantity})>"

