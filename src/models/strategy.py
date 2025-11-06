"""
Strategy Models - Strategy tracking and signals
"""
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class Strategy(Base):
    """Strategy model"""
    __tablename__ = 'strategies'
    
    strategy_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    version = Column(String(20), nullable=False)
    strategy_type = Column(String(50), nullable=False)  # SCALPER, TREND, ARBITRAGE, etc.
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_backtested = Column(Boolean, default=False)
    
    # Configuration (JSON)
    config = Column(JSON, nullable=True)
    parameters = Column(JSON, nullable=True)
    
    # Performance
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    
    total_pnl = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_signal_at = Column(DateTime, nullable=True)
    
    # Relationships
    signals = relationship("Signal", back_populates="strategy", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="strategy")
    positions = relationship("Position", back_populates="strategy")
    performance_records = relationship("StrategyPerformance", back_populates="strategy", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Strategy(name='{self.name}', type='{self.strategy_type}', active={self.is_active})>"


class Signal(Base):
    """Trading signal model"""
    __tablename__ = 'signals'
    
    signal_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id = Column(String(36), ForeignKey('strategies.strategy_id'), nullable=False, index=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)  # ENTRY, EXIT, CLOSE
    direction = Column(String(10), nullable=False)  # LONG, SHORT, NEUTRAL
    
    # Signal details
    confidence = Column(Float, nullable=False)
    strength = Column(Float, nullable=False)
    
    # Prices
    current_price = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    
    # Metadata
    indicators = Column(JSON, nullable=True)  # JSON of indicator values
    conditions = Column(Text, nullable=True)
    
    # Execution
    is_executed = Column(Boolean, default=False, index=True)
    executed_at = Column(DateTime, nullable=True)
    order_id = Column(String(36), nullable=True)
    
    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="signals")
    
    def __repr__(self):
        return f"<Signal(symbol='{self.symbol}', direction='{self.direction}', confidence={self.confidence})>"


class StrategyPerformance(Base):
    """Daily strategy performance tracking"""
    __tablename__ = 'strategy_performance'
    
    performance_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id = Column(String(36), ForeignKey('strategies.strategy_id'), nullable=False, index=True)
    
    date = Column(DateTime, nullable=False, index=True)
    
    # Daily metrics
    trades_count = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    daily_pnl = Column(Float, default=0.0)
    daily_return_pct = Column(Float, default=0.0)
    cumulative_pnl = Column(Float, default=0.0)
    
    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    
    # Volume
    total_volume = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="performance_records")
    
    def __repr__(self):
        return f"<StrategyPerformance(strategy_id='{self.strategy_id}', date='{self.date}', pnl={self.daily_pnl})>"

