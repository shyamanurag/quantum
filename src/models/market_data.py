"""
Market Data Models
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class Symbol(Base):
    """Trading symbol information"""
    __tablename__ = 'symbols'
    
    symbol_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    base_asset = Column(String(10), nullable=False)
    quote_asset = Column(String(10), nullable=False)
    
    # Trading rules
    min_quantity = Column(Float, nullable=True)
    max_quantity = Column(Float, nullable=True)
    step_size = Column(Float, nullable=True)
    min_notional = Column(Float, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_trading = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Symbol(symbol='{self.symbol}', active={self.is_active})>"


class OHLCV(Base):
    """OHLCV candlestick data (1-minute base)"""
    __tablename__ = 'ohlcv'
    
    ohlcv_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String(20), nullable=False, index=True)
    interval = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d
    
    timestamp = Column(DateTime, nullable=False, index=True)
    
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    quote_volume = Column(Float, nullable=True)
    trades_count = Column(Integer, nullable=True)
    
    # Calculated fields
    vwap = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_ohlcv_symbol_interval_timestamp', 'symbol', 'interval', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<OHLCV(symbol='{self.symbol}', timestamp='{self.timestamp}', close={self.close})>"


class MarketData(Base):
    """Real-time market data snapshots"""
    __tablename__ = 'market_data'
    
    market_data_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Price
    last_price = Column(Float, nullable=False)
    bid_price = Column(Float, nullable=True)
    ask_price = Column(Float, nullable=True)
    spread = Column(Float, nullable=True)
    
    # Volume
    volume_24h = Column(Float, nullable=True)
    quote_volume_24h = Column(Float, nullable=True)
    
    # Change
    price_change_24h = Column(Float, nullable=True)
    price_change_pct_24h = Column(Float, nullable=True)
    
    # Order book
    bid_depth = Column(Float, nullable=True)
    ask_depth = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_market_data_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<MarketData(symbol='{self.symbol}', price={self.last_price})>"
