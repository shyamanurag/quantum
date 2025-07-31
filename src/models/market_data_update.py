"""
Market Data Update Model
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class MarketDataUpdate:
    """Unified market data update structure"""
    symbol: str
    price: float
    volume: int
    timestamp: str
    change: float = 0.0
    change_percent: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0
    additional_data: Optional[dict] = None
