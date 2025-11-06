"""
Risk Management Models
"""
from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class RiskEvent(Base):
    """Risk event tracking"""
    __tablename__ = 'risk_events'
    
    event_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(50), nullable=False, index=True)  # CIRCUIT_BREAKER, STOP_LOSS, etc.
    severity = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    
    symbol = Column(String(20), nullable=True, index=True)
    description = Column(Text, nullable=False)
    
    # Metrics at time of event
    portfolio_value = Column(Float, nullable=True)
    daily_pnl = Column(Float, nullable=True)
    position_count = Column(Integer, nullable=True)
    
    # Action taken
    action_taken = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<RiskEvent(type='{self.event_type}', severity='{self.severity}')>"


class Drawdown(Base):
    """Drawdown tracking"""
    __tablename__ = 'drawdowns'
    
    drawdown_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime, nullable=True)
    
    peak_value = Column(Float, nullable=False)
    trough_value = Column(Float, nullable=False)
    recovery_value = Column(Float, nullable=True)
    
    drawdown_amount = Column(Float, nullable=False)
    drawdown_pct = Column(Float, nullable=False)
    
    duration_days = Column(Float, nullable=True)
    recovery_days = Column(Float, nullable=True)
    
    is_recovered = Column(Boolean, default=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Drawdown(drawdown_pct={self.drawdown_pct}%, recovered={self.is_recovered})>"


class PortfolioSnapshot(Base):
    """Portfolio snapshot for tracking equity curve"""
    __tablename__ = 'portfolio_snapshots'
    
    snapshot_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Portfolio value
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    positions_value = Column(Float, nullable=False)
    
    # P&L
    daily_pnl = Column(Float, default=0.0)
    daily_return_pct = Column(Float, default=0.0)
    cumulative_pnl = Column(Float, default=0.0)
    cumulative_return_pct = Column(Float, default=0.0)
    
    # Positions
    open_positions = Column(Integer, default=0)
    
    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_portfolio_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<PortfolioSnapshot(value={self.total_value}, pnl={self.daily_pnl})>"

