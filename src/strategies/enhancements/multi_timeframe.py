"""
Multi-Timeframe Analysis

Analyzes multiple timeframes simultaneously for confluence.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Timeframe(Enum):
    """Supported timeframes"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class TrendDirection(Enum):
    """Trend direction"""
    STRONG_UP = "strong_up"
    UP = "up"
    NEUTRAL = "neutral"
    DOWN = "down"
    STRONG_DOWN = "strong_down"


@dataclass
class TimeframeAnalysis:
    """Analysis for single timeframe"""
    timeframe: Timeframe
    trend: TrendDirection
    trend_strength: float  # 0-1
    volatility: float
    volume_ratio: float  # current / average
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    key_level_distance_pct: float = 0.0


@dataclass
class MultiTimeframeSignal:
    """Multi-timeframe confluence signal"""
    symbol: str
    timestamp: datetime
    
    # Timeframe analyses
    analyses: Dict[Timeframe, TimeframeAnalysis]
    
    # Confluence
    trend_alignment: float  # 0-1 (all timeframes agree)
    strength_score: float  # 0-100
    
    # Signal
    signal_direction: str  # 'BUY', 'SELL', 'NEUTRAL'
    confidence: float  # 0-1
    
    # Key levels
    nearest_support: Optional[float] = None
    nearest_resistance: Optional[float] = None


class MultiTimeframeAnalyzer:
    """
    Analyzes multiple timeframes for trading confluence.
    
    Key concept: Higher timeframes provide context, lower timeframes provide entry.
    
    Hierarchy:
    - D1/H4: Market structure, major support/resistance
    - H1: Trend direction
    - M15/M5: Entry timing
    - M1: Execution
    """
    
    def __init__(
        self,
        primary_timeframes: List[Timeframe] = None
    ):
        self.primary_timeframes = primary_timeframes or [
            Timeframe.M5,
            Timeframe.M15,
            Timeframe.H1,
            Timeframe.H4
        ]
        
        # Storage for historical data
        self.data: Dict[str, Dict[Timeframe, List[Dict]]] = {}
        
        logger.info(
            f"MultiTimeframeAnalyzer initialized with timeframes: "
            f"{[tf.value for tf in self.primary_timeframes]}"
        )
    
    def add_data(
        self,
        symbol: str,
        timeframe: Timeframe,
        ohlcv: List[Dict]  # List of {open, high, low, close, volume, timestamp}
    ):
        """Add OHLCV data for a timeframe"""
        if symbol not in self.data:
            self.data[symbol] = {}
        
        self.data[symbol][timeframe] = ohlcv
    
    def analyze(self, symbol: str) -> Optional[MultiTimeframeSignal]:
        """Analyze all timeframes and generate signal"""
        if symbol not in self.data:
            logger.warning(f"No data for {symbol}")
            return None
        
        # Analyze each timeframe
        analyses: Dict[Timeframe, TimeframeAnalysis] = {}
        
        for tf in self.primary_timeframes:
            if tf not in self.data[symbol]:
                logger.warning(f"Missing {tf.value} data for {symbol}")
                continue
            
            analysis = self._analyze_timeframe(
                symbol, tf, self.data[symbol][tf]
            )
            if analysis:
                analyses[tf] = analysis
        
        if not analyses:
            return None
        
        # Calculate confluence
        trend_alignment = self._calculate_trend_alignment(analyses)
        strength_score = self._calculate_strength_score(analyses)
        
        # Determine signal
        signal_direction, confidence = self._determine_signal(
            analyses, trend_alignment, strength_score
        )
        
        # Find key levels
        nearest_support, nearest_resistance = self._find_key_levels(analyses)
        
        return MultiTimeframeSignal(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            analyses=analyses,
            trend_alignment=trend_alignment,
            strength_score=strength_score,
            signal_direction=signal_direction,
            confidence=confidence,
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance
        )
    
    def _analyze_timeframe(
        self,
        symbol: str,
        timeframe: Timeframe,
        ohlcv: List[Dict]
    ) -> Optional[TimeframeAnalysis]:
        """Analyze single timeframe"""
        if len(ohlcv) < 20:
            return None
        
        # Extract data
        closes = np.array([bar['close'] for bar in ohlcv[-50:]])
        highs = np.array([bar['high'] for bar in ohlcv[-50:]])
        lows = np.array([bar['low'] for bar in ohlcv[-50:]])
        volumes = np.array([bar['volume'] for bar in ohlcv[-50:]])
        
        # Calculate trend
        trend, trend_strength = self._calculate_trend(closes)
        
        # Calculate volatility
        returns = np.diff(np.log(closes))
        volatility = np.std(returns) * np.sqrt(252)  # Annualized
        
        # Volume ratio
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-20:-1])
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Support and resistance
        support = self._find_support(lows)
        resistance = self._find_resistance(highs)
        
        # Distance to key levels
        current_price = closes[-1]
        dist_to_support = abs(current_price - support) / current_price if support else 0
        dist_to_resistance = abs(current_price - resistance) / current_price if resistance else 0
        key_level_distance = min(dist_to_support, dist_to_resistance)
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            trend=trend,
            trend_strength=trend_strength,
            volatility=volatility,
            volume_ratio=volume_ratio,
            support_level=support,
            resistance_level=resistance,
            key_level_distance_pct=key_level_distance
        )
    
    def _calculate_trend(self, closes: np.ndarray) -> Tuple[TrendDirection, float]:
        """Calculate trend direction and strength"""
        # Simple: linear regression slope
        x = np.arange(len(closes))
        coeffs = np.polyfit(x, closes, 1)
        slope = coeffs[0]
        
        # Normalize slope
        price_range = np.max(closes) - np.min(closes)
        normalized_slope = slope / (price_range / len(closes)) if price_range > 0 else 0
        
        # Trend strength (R-squared)
        fitted = np.polyval(coeffs, x)
        ss_res = np.sum((closes - fitted) ** 2)
        ss_tot = np.sum((closes - np.mean(closes)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        trend_strength = max(0, min(1, r_squared))
        
        # Classify trend
        if normalized_slope > 0.5:
            trend = TrendDirection.STRONG_UP
        elif normalized_slope > 0.1:
            trend = TrendDirection.UP
        elif normalized_slope < -0.5:
            trend = TrendDirection.STRONG_DOWN
        elif normalized_slope < -0.1:
            trend = TrendDirection.DOWN
        else:
            trend = TrendDirection.NEUTRAL
        
        return trend, trend_strength
    
    def _find_support(self, lows: np.ndarray) -> Optional[float]:
        """Find nearest support level"""
        if len(lows) < 10:
            return None
        
        # Simple: recent low
        return np.min(lows[-20:])
    
    def _find_resistance(self, highs: np.ndarray) -> Optional[float]:
        """Find nearest resistance level"""
        if len(highs) < 10:
            return None
        
        # Simple: recent high
        return np.max(highs[-20:])
    
    def _calculate_trend_alignment(
        self,
        analyses: Dict[Timeframe, TimeframeAnalysis]
    ) -> float:
        """Calculate how aligned trends are across timeframes"""
        if not analyses:
            return 0.0
        
        # Convert trends to numeric values
        trend_values = {
            TrendDirection.STRONG_UP: 2,
            TrendDirection.UP: 1,
            TrendDirection.NEUTRAL: 0,
            TrendDirection.DOWN: -1,
            TrendDirection.STRONG_DOWN: -2
        }
        
        numeric_trends = [
            trend_values[analysis.trend] for analysis in analyses.values()
        ]
        
        # Calculate alignment (1 = all same direction, 0 = random)
        if not numeric_trends:
            return 0.0
        
        mean_trend = np.mean(numeric_trends)
        std_trend = np.std(numeric_trends)
        
        # High alignment = low std
        alignment = max(0, min(1, 1 - (std_trend / 2)))
        
        return alignment
    
    def _calculate_strength_score(
        self,
        analyses: Dict[Timeframe, TimeframeAnalysis]
    ) -> float:
        """Calculate overall signal strength (0-100)"""
        if not analyses:
            return 0.0
        
        # Average trend strength across timeframes
        avg_strength = np.mean([a.trend_strength for a in analyses.values()])
        
        # Bonus for all timeframes being strong
        all_strong = all(a.trend_strength > 0.7 for a in analyses.values())
        
        score = avg_strength * 100
        if all_strong:
            score = min(100, score * 1.2)
        
        return score
    
    def _determine_signal(
        self,
        analyses: Dict[Timeframe, TimeframeAnalysis],
        trend_alignment: float,
        strength_score: float
    ) -> Tuple[str, float]:
        """Determine final signal and confidence"""
        if not analyses or trend_alignment < 0.6:
            return 'NEUTRAL', 0.0
        
        # Count bullish vs bearish timeframes
        bullish_count = sum(
            1 for a in analyses.values()
            if a.trend in [TrendDirection.UP, TrendDirection.STRONG_UP]
        )
        bearish_count = sum(
            1 for a in analyses.values()
            if a.trend in [TrendDirection.DOWN, TrendDirection.STRONG_DOWN]
        )
        
        # Determine direction
        if bullish_count > bearish_count and bullish_count >= len(analyses) * 0.6:
            signal_direction = 'BUY'
        elif bearish_count > bullish_count and bearish_count >= len(analyses) * 0.6:
            signal_direction = 'SELL'
        else:
            signal_direction = 'NEUTRAL'
        
        # Calculate confidence
        confidence = (trend_alignment + (strength_score / 100)) / 2
        
        return signal_direction, confidence
    
    def _find_key_levels(
        self,
        analyses: Dict[Timeframe, TimeframeAnalysis]
    ) -> Tuple[Optional[float], Optional[float]]:
        """Find nearest support and resistance across all timeframes"""
        supports = [a.support_level for a in analyses.values() if a.support_level]
        resistances = [a.resistance_level for a in analyses.values() if a.resistance_level]
        
        nearest_support = max(supports) if supports else None
        nearest_resistance = min(resistances) if resistances else None
        
        return nearest_support, nearest_resistance



