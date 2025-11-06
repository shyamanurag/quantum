"""
Footprint Chart Analysis

Advanced order flow visualization and analysis for institutional trading.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class FootprintBar:
    """Single bar in footprint chart"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    
    # Volume at each price level
    price_levels: Dict[float, Dict[str, float]] = field(default_factory=dict)
    # price -> {'bid_volume': X, 'ask_volume': Y, 'delta': Z}
    
    # Aggregates
    total_bid_volume: float = 0.0
    total_ask_volume: float = 0.0
    delta: float = 0.0  # bid - ask
    cumulative_delta: float = 0.0
    
    # Flags
    has_absorption: bool = False
    has_exhaustion: bool = False
    has_imbalance: bool = False


class FootprintAnalyzer:
    """
    Analyzes order flow using footprint charts.
    
    Key patterns:
    1. Delta Divergence - price up but delta down (bearish)
    2. Absorption - large volume but small price move (supply/demand)
    3. Exhaustion - decreasing volume at price extremes (reversal)
    4. Imbalance - one-sided volume (continuation signal)
    """
    
    def __init__(self, bar_size_minutes: int = 1, price_tick_size: float = 0.1):
        self.bar_size_minutes = bar_size_minutes
        self.price_tick_size = price_tick_size
        
        # Storage
        self.bars: Dict[str, List[FootprintBar]] = defaultdict(list)
        self.current_bars: Dict[str, Optional[FootprintBar]] = {}
        
        # Cumulative delta tracking
        self.cumulative_delta: Dict[str, float] = defaultdict(float)
        
        logger.info(f"FootprintAnalyzer initialized: {bar_size_minutes}min bars")
    
    async def add_trade(
        self,
        symbol: str,
        price: float,
        volume: float,
        side: str,  # 'BUY' or 'SELL'
        timestamp: datetime
    ):
        """Add trade to footprint chart"""
        # Get or create current bar
        if symbol not in self.current_bars or self.current_bars[symbol] is None:
            self.current_bars[symbol] = FootprintBar(
                timestamp=timestamp,
                open=price,
                high=price,
                low=price,
                close=price
            )
        
        bar = self.current_bars[symbol]
        
        # Check if we need to close the current bar
        if (timestamp - bar.timestamp).total_seconds() >= self.bar_size_minutes * 60:
            # Close current bar and start new one
            await self._close_bar(symbol, bar)
            bar = FootprintBar(
                timestamp=timestamp,
                open=price,
                high=price,
                low=price,
                close=price
            )
            self.current_bars[symbol] = bar
        
        # Update OHLC
        bar.high = max(bar.high, price)
        bar.low = min(bar.low, price)
        bar.close = price
        
        # Round price to tick size
        price_level = round(price / self.price_tick_size) * self.price_tick_size
        
        # Initialize price level if needed
        if price_level not in bar.price_levels:
            bar.price_levels[price_level] = {
                'bid_volume': 0.0,
                'ask_volume': 0.0,
                'delta': 0.0
            }
        
        # Add volume
        if side == 'BUY':
            bar.price_levels[price_level]['ask_volume'] += volume
            bar.total_ask_volume += volume
            delta_change = volume
        else:  # SELL
            bar.price_levels[price_level]['bid_volume'] += volume
            bar.total_bid_volume += volume
            delta_change = -volume
        
        # Update deltas
        bar.price_levels[price_level]['delta'] = (
            bar.price_levels[price_level]['ask_volume'] - 
            bar.price_levels[price_level]['bid_volume']
        )
        bar.delta = bar.total_ask_volume - bar.total_bid_volume
        self.cumulative_delta[symbol] += delta_change
        bar.cumulative_delta = self.cumulative_delta[symbol]
    
    async def _close_bar(self, symbol: str, bar: FootprintBar):
        """Close bar and analyze patterns"""
        # Detect patterns
        bar.has_absorption = self._detect_absorption(bar)
        bar.has_exhaustion = self._detect_exhaustion(bar, symbol)
        bar.has_imbalance = self._detect_imbalance(bar)
        
        # Store bar
        self.bars[symbol].append(bar)
        
        # Keep only last 1000 bars
        if len(self.bars[symbol]) > 1000:
            self.bars[symbol] = self.bars[symbol][-1000:]
        
        logger.debug(
            f"Closed footprint bar {symbol}: delta={bar.delta:.2f}, "
            f"absorption={bar.has_absorption}, imbalance={bar.has_imbalance}"
        )
    
    def _detect_absorption(self, bar: FootprintBar) -> bool:
        """
        Detect absorption: High volume but small price range.
        Indicates strong support/resistance.
        """
        if bar.total_ask_volume + bar.total_bid_volume == 0:
            return False
        
        total_volume = bar.total_ask_volume + bar.total_bid_volume
        price_range = bar.high - bar.low
        
        # High volume (>2x average) but small range (<0.2%)
        avg_volume = np.mean([b.total_ask_volume + b.total_bid_volume 
                             for b in list(self.bars.get(bar.timestamp, []))[-20:]])
        
        if avg_volume == 0:
            return False
        
        volume_ratio = total_volume / avg_volume
        range_pct = price_range / bar.close if bar.close > 0 else 0
        
        return volume_ratio > 2.0 and range_pct < 0.002  # <0.2%
    
    def _detect_exhaustion(self, bar: FootprintBar, symbol: str) -> bool:
        """
        Detect exhaustion: Decreasing volume at price extremes.
        Potential reversal signal.
        """
        bars = self.bars.get(symbol, [])
        if len(bars) < 3:
            return False
        
        recent = bars[-3:]
        volumes = [b.total_ask_volume + b.total_bid_volume for b in recent]
        
        # Volume declining for 3 bars
        return volumes[0] > volumes[1] > volumes[2] > 0
    
    def _detect_imbalance(self, bar: FootprintBar) -> bool:
        """
        Detect order flow imbalance: One-sided volume.
        Strong continuation signal.
        """
        if bar.total_ask_volume + bar.total_bid_volume == 0:
            return False
        
        imbalance_ratio = abs(bar.delta) / (bar.total_ask_volume + bar.total_bid_volume)
        
        # >70% one-sided
        return imbalance_ratio > 0.7
    
    def detect_delta_divergence(self, symbol: str, lookback: int = 10) -> Optional[str]:
        """
        Detect delta divergence: Price and delta moving in opposite directions.
        
        Returns:
            'BULLISH' if price down but delta up (buying pressure)
            'BEARISH' if price up but delta down (selling pressure)
            None if no divergence
        """
        bars = self.bars.get(symbol, [])
        if len(bars) < lookback:
            return None
        
        recent = bars[-lookback:]
        
        # Calculate price trend
        price_change = recent[-1].close - recent[0].close
        
        # Calculate delta trend
        delta_change = recent[-1].cumulative_delta - recent[0].cumulative_delta
        
        # Divergence: opposite signs
        if price_change > 0 and delta_change < 0:
            # Price up, delta down = BEARISH
            if abs(delta_change) > abs(price_change) * 100:  # Significant
                return 'BEARISH'
        elif price_change < 0 and delta_change > 0:
            # Price down, delta up = BULLISH
            if abs(delta_change) > abs(price_change) * 100:
                return 'BULLISH'
        
        return None
    
    def get_current_delta(self, symbol: str) -> float:
        """Get current cumulative delta"""
        return self.cumulative_delta.get(symbol, 0.0)
    
    def get_volume_profile_for_range(
        self,
        symbol: str,
        lookback_bars: int = 20
    ) -> Dict[float, float]:
        """Get volume profile (price -> volume) for recent range"""
        bars = self.bars.get(symbol, [])[-lookback_bars:]
        
        volume_by_price = defaultdict(float)
        for bar in bars:
            for price, data in bar.price_levels.items():
                volume_by_price[price] += data['bid_volume'] + data['ask_volume']
        
        return dict(volume_by_price)
    
    def get_point_of_control(self, symbol: str, lookback_bars: int = 20) -> Optional[float]:
        """Get Point of Control (price with highest volume)"""
        volume_profile = self.get_volume_profile_for_range(symbol, lookback_bars)
        if not volume_profile:
            return None
        
        return max(volume_profile.items(), key=lambda x: x[1])[0]



