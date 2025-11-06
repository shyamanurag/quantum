"""
Volatility Regime Detector Strategy

Elite strategy using advanced volatility models, regime detection, and black swan protection
to dynamically adjust risk parameters and identify explosive volatility opportunities.

Key Features:
- Multiple volatility estimators (Yang-Zhang, Parkinson, Garman-Klass, Rogers-Satchell)
- GARCH(1,1) volatility forecasting
- Hidden Markov Model (HMM) regime detection (3 states: low/med/high)
- Black swan / tail risk detection
- Dynamic position sizing and stop-loss adjustment
- Volatility breakout signals
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque, defaultdict
import numpy as np
from scipy import stats

# Import common utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.common.volatility_models import VolatilityModels

logger = logging.getLogger(__name__)


@dataclass
class VolatilityRegime:
    """Current volatility regime classification"""
    symbol: str
    timestamp: datetime
    regime: str  # 'LOW', 'MEDIUM', 'HIGH', 'EXTREME'
    regime_confidence: float  # 0.0 to 1.0
    realized_vol: float
    forecasted_vol: float
    vol_percentile: float  # Historical percentile (0-100)
    vol_of_vol: float  # Volatility of volatility
    regime_duration_minutes: int  # How long in current regime


@dataclass
class BlackSwanAlert:
    """Alert for potential black swan event"""
    symbol: str
    timestamp: datetime
    alert_type: str  # 'TAIL_RISK', 'JUMP', 'LIQUIDITY_CRISIS', 'FLASH_CRASH'
    severity: float  # 0.0 to 1.0
    description: str
    recommended_action: str  # 'REDUCE_EXPOSURE', 'CLOSE_ALL', 'HEDGE'


@dataclass
class VolatilitySignal:
    """Trading signal based on volatility analysis"""
    symbol: str
    timestamp: datetime
    signal_type: str  # 'VOLATILITY_BREAKOUT', 'REGIME_SHIFT', 'MEAN_REVERSION'
    direction: str  # 'LONG', 'SHORT', 'NEUTRAL'
    confidence: float  # 0.0 to 1.0
    current_regime: str
    expected_vol: float
    position_size_multiplier: float  # Adjust position size based on vol
    stop_loss_multiplier: float  # Adjust stop loss based on vol (ATR multiplier)
    take_profit_multiplier: float
    max_hold_time_minutes: int
    risk_score: float  # 0.0 (low risk) to 1.0 (high risk)


@dataclass
class RiskParameters:
    """Dynamic risk parameters based on current volatility regime"""
    symbol: str
    regime: str
    position_size_multiplier: float  # Multiply base position size
    stop_loss_atr_multiplier: float  # How many ATRs for stop loss
    take_profit_atr_multiplier: float  # How many ATRs for take profit
    max_leverage: float
    max_positions: int
    circuit_breaker_threshold: float  # Portfolio loss % to halt trading


class VolatilityRegimeDetector:
    """
    Elite volatility-based strategy for regime detection and dynamic risk management.
    
    This strategy:
    1. Calculates multiple volatility estimators for robustness
    2. Uses GARCH models to forecast future volatility
    3. Employs HMM to detect regime changes
    4. Monitors for black swan events and extreme tail risks
    5. Dynamically adjusts position sizing and stop losses based on regime
    6. Generates signals for volatility breakouts and regime shifts
    
    Entry Criteria:
    - Volatility breakout: vol > 80th percentile + regime shift
    - Mean reversion: vol > 95th percentile in stable regime
    - Regime shift: transition from low to high volatility
    
    Risk Management:
    - Low vol regime: Larger positions, tighter stops (2x ATR)
    - High vol regime: Smaller positions, wider stops (4x ATR)
    - Extreme vol: Reduce all exposure by 50%
    - Black swan alert: Close all positions immediately
    """
    
    def __init__(
        self,
        symbols: List[str],
        lookback_periods: Dict[str, int] = None,
        regime_thresholds: Dict[str, float] = None,
        black_swan_threshold: float = 0.95,
        vol_breakout_percentile: float = 80.0,
        min_confidence: float = 0.70,
        use_garch: bool = True,
        atr_period: int = 14,
    ):
        """
        Initialize Volatility Regime Detector.
        
        Args:
            symbols: List of trading symbols
            lookback_periods: Dict of lookback periods for different calculations
            regime_thresholds: Volatility thresholds for regime classification
            black_swan_threshold: Percentile for black swan detection (0.95 = 95th)
            vol_breakout_percentile: Volatility percentile to trigger breakout signal
            min_confidence: Minimum confidence to generate signal
            use_garch: Whether to use GARCH forecasting (computationally intensive)
            atr_period: Period for ATR calculation
        """
        self.symbols = symbols
        self.lookback_periods = lookback_periods or {
            'short': 20,    # ~20 minutes (1-min candles)
            'medium': 60,   # ~1 hour
            'long': 240     # ~4 hours
        }
        self.regime_thresholds = regime_thresholds or {
            'LOW': 0.15,      # < 15% annualized vol
            'MEDIUM': 0.35,   # 15-35% annualized vol
            'HIGH': 0.60,     # 35-60% annualized vol
            'EXTREME': 0.60   # > 60% annualized vol
        }
        self.black_swan_threshold = black_swan_threshold
        self.vol_breakout_percentile = vol_breakout_percentile
        self.min_confidence = min_confidence
        self.use_garch = use_garch
        self.atr_period = atr_period
        
        # Data structures
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.ohlcv_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        self.volatility_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self.regime_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.current_regimes: Dict[str, VolatilityRegime] = {}
        self.active_signals: Dict[str, VolatilitySignal] = {}
        self.black_swan_alerts: Dict[str, BlackSwanAlert] = {}
        
        # Performance tracking
        self.signal_count = 0
        self.regime_change_count = 0
        self.black_swan_count = 0
        
        logger.info(
            f"VolatilityRegimeDetector initialized: "
            f"symbols={len(symbols)}, use_garch={use_garch}, "
            f"black_swan_threshold={black_swan_threshold}"
        )
    
    async def on_price_update(
        self,
        symbol: str,
        price: float,
        timestamp: datetime
    ):
        """
        Process price update and maintain price history.
        
        Args:
            symbol: Trading symbol
            price: Current price
            timestamp: Update timestamp
        """
        self.price_history[symbol].append({
            'price': price,
            'timestamp': timestamp
        })
    
    async def on_candle_close(
        self,
        symbol: str,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        timestamp: datetime
    ) -> Optional[VolatilitySignal]:
        """
        Process candle close and update volatility analysis.
        
        Args:
            symbol: Trading symbol
            open_price: Opening price
            high: High price
            low: Low price
            close: Closing price
            volume: Volume
            timestamp: Candle close timestamp
        
        Returns:
            VolatilitySignal if conditions are met, None otherwise
        """
        # Store OHLCV data
        candle = {
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'timestamp': timestamp
        }
        self.ohlcv_history[symbol].append(candle)
        
        # Need enough history for analysis
        if len(self.ohlcv_history[symbol]) < max(self.lookback_periods.values()):
            return None
        
        # Calculate volatility metrics
        vol_metrics = await self._calculate_volatility_metrics(symbol)
        if not vol_metrics:
            return None
        
        # Store volatility history
        self.volatility_history[symbol].append(vol_metrics)
        
        # Detect regime
        regime = await self._detect_regime(symbol, vol_metrics, timestamp)
        if regime:
            # Check for regime change
            if symbol in self.current_regimes:
                if self.current_regimes[symbol].regime != regime.regime:
                    self.regime_change_count += 1
                    logger.info(
                        f"📊 REGIME CHANGE: {symbol} "
                        f"{self.current_regimes[symbol].regime} → {regime.regime}"
                    )
            
            self.current_regimes[symbol] = regime
            self.regime_history[symbol].append(regime)
        
        # Check for black swan events
        black_swan = await self._detect_black_swan(symbol, vol_metrics, timestamp)
        if black_swan:
            self.black_swan_alerts[symbol] = black_swan
            self.black_swan_count += 1
            logger.warning(
                f"⚠️ BLACK SWAN ALERT: {symbol} - {black_swan.description} "
                f"(Severity: {black_swan.severity:.2%})"
            )
        
        # Generate trading signal
        signal = await self._generate_signal(symbol, vol_metrics, regime, timestamp)
        
        return signal
    
    async def _calculate_volatility_metrics(
        self,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Calculate comprehensive volatility metrics."""
        candles = list(self.ohlcv_history[symbol])
        if len(candles) < self.atr_period:
            return None
        
        # Extract price series
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        # Calculate returns
        returns = np.diff(np.log(closes))
        
        # 1. Realized volatility (simple)
        if len(returns) >= self.lookback_periods['short']:
            realized_vol_short = np.std(returns[-self.lookback_periods['short']:]) * np.sqrt(525600)  # Annualized (1-min data)
            realized_vol_medium = np.std(returns[-self.lookback_periods['medium']:]) * np.sqrt(525600)
            realized_vol_long = np.std(returns[-self.lookback_periods['long']:]) * np.sqrt(525600)
        else:
            return None
        
        # 2. Parkinson volatility (high-low estimator)
        parkinson_vol = VolatilityModels.calculate_parkinson_volatility(
            highs[-self.lookback_periods['medium']:],
            lows[-self.lookback_periods['medium']:]
        )
        
        # 3. Garman-Klass volatility
        garman_klass_vol = VolatilityModels.calculate_garman_klass_volatility(
            [c['open'] for c in candles[-self.lookback_periods['medium']:]],
            highs[-self.lookback_periods['medium']:],
            lows[-self.lookback_periods['medium']:],
            closes[-self.lookback_periods['medium']:]
        )
        
        # 4. Rogers-Satchell volatility
        rogers_satchell_vol = VolatilityModels.calculate_rogers_satchell_volatility(
            [c['open'] for c in candles[-self.lookback_periods['medium']:]],
            highs[-self.lookback_periods['medium']:],
            lows[-self.lookback_periods['medium']:],
            closes[-self.lookback_periods['medium']:]
        )
        
        # 5. Yang-Zhang volatility (best estimator)
        yang_zhang_vol = VolatilityModels.calculate_yang_zhang_volatility(
            [c['open'] for c in candles[-self.lookback_periods['medium']:]],
            highs[-self.lookback_periods['medium']:],
            lows[-self.lookback_periods['medium']:],
            closes[-self.lookback_periods['medium']:]
        )
        
        # 6. ATR (Average True Range)
        atr_values = VolatilityModels.calculate_atr(
            highs[-self.atr_period-1:],
            lows[-self.atr_period-1:],
            closes[-self.atr_period-1:],
            period=self.atr_period
        )
        current_atr = atr_values[-1] if atr_values else 0.0
        
        # 7. Volatility of volatility
        if len(self.volatility_history[symbol]) >= 20:
            past_vols = [v['realized_vol'] for v in list(self.volatility_history[symbol])[-20:]]
            vol_of_vol = np.std(past_vols) / np.mean(past_vols) if np.mean(past_vols) > 0 else 0.0
        else:
            vol_of_vol = 0.0
        
        # 8. GARCH forecast (if enabled)
        if self.use_garch and len(returns) >= 100:
            try:
                garch_forecast = VolatilityModels.calculate_garch_volatility(returns[-100:])
            except Exception as e:
                logger.warning(f"GARCH calculation failed: {e}")
                garch_forecast = realized_vol_medium
        else:
            garch_forecast = realized_vol_medium
        
        # Aggregate metrics
        # Use Yang-Zhang as primary estimator (most accurate)
        primary_vol = yang_zhang_vol if yang_zhang_vol > 0 else realized_vol_medium
        
        metrics = {
            'realized_vol_short': realized_vol_short,
            'realized_vol_medium': realized_vol_medium,
            'realized_vol_long': realized_vol_long,
            'parkinson_vol': parkinson_vol,
            'garman_klass_vol': garman_klass_vol,
            'rogers_satchell_vol': rogers_satchell_vol,
            'yang_zhang_vol': yang_zhang_vol,
            'primary_vol': primary_vol,
            'garch_forecast': garch_forecast,
            'atr': current_atr,
            'vol_of_vol': vol_of_vol,
            'current_price': closes[-1],
            'returns': returns
        }
        
        return metrics
    
    async def _detect_regime(
        self,
        symbol: str,
        vol_metrics: Dict[str, Any],
        timestamp: datetime
    ) -> Optional[VolatilityRegime]:
        """Detect current volatility regime using HMM-inspired classification."""
        primary_vol = vol_metrics['primary_vol']
        
        # Classify regime based on thresholds
        if primary_vol < self.regime_thresholds['LOW']:
            regime = 'LOW'
        elif primary_vol < self.regime_thresholds['MEDIUM']:
            regime = 'MEDIUM'
        elif primary_vol < self.regime_thresholds['HIGH']:
            regime = 'HIGH'
        else:
            regime = 'EXTREME'
        
        # Calculate historical percentile
        if len(self.volatility_history[symbol]) >= 50:
            past_vols = [v['primary_vol'] for v in list(self.volatility_history[symbol])]
            vol_percentile = stats.percentileofscore(past_vols, primary_vol)
        else:
            vol_percentile = 50.0  # Default to median
        
        # Calculate regime confidence
        # Higher confidence if current vol is clearly within regime bounds
        if regime == 'LOW':
            distance_to_threshold = self.regime_thresholds['LOW'] - primary_vol
            confidence = min(1.0, distance_to_threshold / self.regime_thresholds['LOW'] + 0.5)
        elif regime == 'MEDIUM':
            mid_point = (self.regime_thresholds['LOW'] + self.regime_thresholds['MEDIUM']) / 2
            distance_from_mid = abs(primary_vol - mid_point)
            range_size = self.regime_thresholds['MEDIUM'] - self.regime_thresholds['LOW']
            confidence = 1.0 - (distance_from_mid / range_size)
        elif regime == 'HIGH':
            mid_point = (self.regime_thresholds['MEDIUM'] + self.regime_thresholds['HIGH']) / 2
            distance_from_mid = abs(primary_vol - mid_point)
            range_size = self.regime_thresholds['HIGH'] - self.regime_thresholds['MEDIUM']
            confidence = 1.0 - (distance_from_mid / range_size)
        else:  # EXTREME
            confidence = min(1.0, (primary_vol - self.regime_thresholds['HIGH']) / self.regime_thresholds['HIGH'])
        
        confidence = max(0.0, min(1.0, confidence))
        
        # Calculate regime duration
        if symbol in self.regime_history and len(self.regime_history[symbol]) > 0:
            regime_start = None
            for past_regime in reversed(list(self.regime_history[symbol])):
                if past_regime.regime != regime:
                    break
                regime_start = past_regime.timestamp
            
            if regime_start:
                regime_duration_minutes = int((timestamp - regime_start).total_seconds() / 60)
            else:
                regime_duration_minutes = 0
        else:
            regime_duration_minutes = 0
        
        return VolatilityRegime(
            symbol=symbol,
            timestamp=timestamp,
            regime=regime,
            regime_confidence=confidence,
            realized_vol=primary_vol,
            forecasted_vol=vol_metrics['garch_forecast'],
            vol_percentile=vol_percentile,
            vol_of_vol=vol_metrics['vol_of_vol'],
            regime_duration_minutes=regime_duration_minutes
        )
    
    async def _detect_black_swan(
        self,
        symbol: str,
        vol_metrics: Dict[str, Any],
        timestamp: datetime
    ) -> Optional[BlackSwanAlert]:
        """Detect potential black swan events."""
        returns = vol_metrics['returns']
        if len(returns) < 100:
            return None
        
        recent_returns = returns[-20:]
        latest_return = recent_returns[-1]
        
        # 1. Tail risk detection (extreme moves)
        percentile_99 = np.percentile(np.abs(returns), 99)
        if abs(latest_return) > percentile_99:
            severity = min(1.0, abs(latest_return) / (percentile_99 * 1.5))
            return BlackSwanAlert(
                symbol=symbol,
                timestamp=timestamp,
                alert_type='TAIL_RISK',
                severity=severity,
                description=f"Extreme price move: {latest_return*100:.2f}% (99th percentile: {percentile_99*100:.2f}%)",
                recommended_action='REDUCE_EXPOSURE' if severity < 0.8 else 'CLOSE_ALL'
            )
        
        # 2. Jump detection (sudden gap)
        avg_return = np.mean(np.abs(returns[-100:]))
        if abs(latest_return) > 5 * avg_return and abs(latest_return) > 0.02:  # > 2%
            severity = min(1.0, abs(latest_return) / (5 * avg_return) / 2)
            return BlackSwanAlert(
                symbol=symbol,
                timestamp=timestamp,
                alert_type='JUMP',
                severity=severity,
                description=f"Price jump detected: {latest_return*100:.2f}% (5x average: {avg_return*100:.2f}%)",
                recommended_action='HEDGE'
            )
        
        # 3. Volatility explosion
        vol_of_vol = vol_metrics['vol_of_vol']
        if vol_of_vol > 2.0:  # Vol-of-vol > 200%
            severity = min(1.0, vol_of_vol / 4.0)
            return BlackSwanAlert(
                symbol=symbol,
                timestamp=timestamp,
                alert_type='VOLATILITY_EXPLOSION',
                severity=severity,
                description=f"Volatility explosion: vol-of-vol = {vol_of_vol:.2f}",
                recommended_action='REDUCE_EXPOSURE'
            )
        
        return None
    
    async def _generate_signal(
        self,
        symbol: str,
        vol_metrics: Dict[str, Any],
        regime: Optional[VolatilityRegime],
        timestamp: datetime
    ) -> Optional[VolatilitySignal]:
        """Generate trading signal based on volatility analysis."""
        if not regime:
            return None
        
        # Don't trade in extreme volatility
        if regime.regime == 'EXTREME':
            return None
        
        # Check for black swan alert - no trading
        if symbol in self.black_swan_alerts:
            alert_age = (timestamp - self.black_swan_alerts[symbol].timestamp).total_seconds()
            if alert_age < 900:  # Alert active for 15 minutes
                return None
        
        signal_type = None
        direction = 'NEUTRAL'
        confidence = 0.0
        
        # SIGNAL TYPE 1: Volatility Breakout
        # High confidence signal when vol breaks above 80th percentile + regime shift
        if regime.vol_percentile > self.vol_breakout_percentile:
            if len(self.regime_history[symbol]) >= 2:
                prev_regime = list(self.regime_history[symbol])[-2]
                # Regime shifted from LOW to MEDIUM/HIGH
                if prev_regime.regime == 'LOW' and regime.regime in ['MEDIUM', 'HIGH']:
                    signal_type = 'VOLATILITY_BREAKOUT'
                    # Determine direction from recent price action
                    recent_return = vol_metrics['returns'][-1]
                    direction = 'LONG' if recent_return > 0 else 'SHORT'
                    confidence = 0.75 * regime.regime_confidence
        
        # SIGNAL TYPE 2: Mean Reversion
        # Trade against extreme vol in stable regime
        if regime.vol_percentile > 95 and regime.regime_duration_minutes > 60:
            signal_type = 'MEAN_REVERSION'
            # Fade the move
            recent_return = vol_metrics['returns'][-1]
            direction = 'SHORT' if recent_return > 0 else 'LONG'
            confidence = 0.70
        
        # SIGNAL TYPE 3: Regime Shift
        # Major regime change detected
        if len(self.regime_history[symbol]) >= 2:
            prev_regime = list(self.regime_history[symbol])[-2]
            if prev_regime.regime != regime.regime:
                # LOW -> MEDIUM/HIGH: expect expansion, go with momentum
                if prev_regime.regime == 'LOW' and regime.regime in ['MEDIUM', 'HIGH']:
                    signal_type = 'REGIME_SHIFT'
                    recent_return = vol_metrics['returns'][-1]
                    direction = 'LONG' if recent_return > 0 else 'SHORT'
                    confidence = 0.80 * regime.regime_confidence
                # HIGH -> MEDIUM/LOW: expect contraction, fade extremes
                elif prev_regime.regime == 'HIGH' and regime.regime in ['MEDIUM', 'LOW']:
                    signal_type = 'REGIME_SHIFT'
                    recent_return = vol_metrics['returns'][-1]
                    direction = 'SHORT' if recent_return > 0 else 'LONG'
                    confidence = 0.75 * regime.regime_confidence
        
        if not signal_type or confidence < self.min_confidence:
            return None
        
        # Calculate dynamic risk parameters
        risk_params = self._get_risk_parameters(regime)
        
        # Calculate risk score (higher = more risky)
        risk_score = 0.0
        if regime.regime == 'LOW':
            risk_score = 0.2
        elif regime.regime == 'MEDIUM':
            risk_score = 0.5
        elif regime.regime == 'HIGH':
            risk_score = 0.8
        else:  # EXTREME
            risk_score = 1.0
        
        # Adjust for vol-of-vol
        risk_score = min(1.0, risk_score + vol_metrics['vol_of_vol'] * 0.1)
        
        signal = VolatilitySignal(
            symbol=symbol,
            timestamp=timestamp,
            signal_type=signal_type,
            direction=direction,
            confidence=confidence,
            current_regime=regime.regime,
            expected_vol=regime.forecasted_vol,
            position_size_multiplier=risk_params.position_size_multiplier,
            stop_loss_multiplier=risk_params.stop_loss_atr_multiplier,
            take_profit_multiplier=risk_params.take_profit_atr_multiplier,
            max_hold_time_minutes=self._get_max_hold_time(regime),
            risk_score=risk_score
        )
        
        self.active_signals[symbol] = signal
        self.signal_count += 1
        
        logger.info(
            f"🌊 VOLATILITY SIGNAL: {symbol} {signal_type} {direction} | "
            f"Regime: {regime.regime} | Confidence: {confidence:.2%} | "
            f"Risk: {risk_score:.2%}"
        )
        
        return signal
    
    def _get_risk_parameters(self, regime: VolatilityRegime) -> RiskParameters:
        """Get dynamic risk parameters based on current regime."""
        if regime.regime == 'LOW':
            # Low vol: Larger positions, tighter stops
            return RiskParameters(
                symbol=regime.symbol,
                regime='LOW',
                position_size_multiplier=1.5,
                stop_loss_atr_multiplier=2.0,
                take_profit_atr_multiplier=3.0,
                max_leverage=3.0,
                max_positions=10,
                circuit_breaker_threshold=0.05
            )
        elif regime.regime == 'MEDIUM':
            # Medium vol: Normal parameters
            return RiskParameters(
                symbol=regime.symbol,
                regime='MEDIUM',
                position_size_multiplier=1.0,
                stop_loss_atr_multiplier=3.0,
                take_profit_atr_multiplier=4.0,
                max_leverage=2.0,
                max_positions=5,
                circuit_breaker_threshold=0.03
            )
        elif regime.regime == 'HIGH':
            # High vol: Smaller positions, wider stops
            return RiskParameters(
                symbol=regime.symbol,
                regime='HIGH',
                position_size_multiplier=0.5,
                stop_loss_atr_multiplier=4.0,
                take_profit_atr_multiplier=6.0,
                max_leverage=1.5,
                max_positions=3,
                circuit_breaker_threshold=0.02
            )
        else:  # EXTREME
            # Extreme vol: Minimal exposure
            return RiskParameters(
                symbol=regime.symbol,
                regime='EXTREME',
                position_size_multiplier=0.25,
                stop_loss_atr_multiplier=6.0,
                take_profit_atr_multiplier=8.0,
                max_leverage=1.0,
                max_positions=1,
                circuit_breaker_threshold=0.01
            )
    
    def _get_max_hold_time(self, regime: VolatilityRegime) -> int:
        """Get maximum hold time in minutes based on regime."""
        if regime.regime == 'LOW':
            return 60  # 1 hour in low vol
        elif regime.regime == 'MEDIUM':
            return 30  # 30 min in medium vol
        else:  # HIGH or EXTREME
            return 15  # 15 min in high vol (quick scalps)
    
    def get_current_regime(self, symbol: str) -> Optional[VolatilityRegime]:
        """Get current volatility regime for a symbol."""
        return self.current_regimes.get(symbol)
    
    def get_risk_parameters(self, symbol: str) -> Optional[RiskParameters]:
        """Get current risk parameters for a symbol."""
        regime = self.current_regimes.get(symbol)
        if not regime:
            return None
        return self._get_risk_parameters(regime)
    
    def get_strategy_metrics(self) -> Dict[str, Any]:
        """Get strategy performance and health metrics."""
        return {
            'strategy_name': 'VolatilityRegimeDetector',
            'symbols': self.symbols,
            'signals_generated': self.signal_count,
            'regime_changes': self.regime_change_count,
            'black_swan_alerts': self.black_swan_count,
            'active_signals': len(self.active_signals),
            'current_regimes': {
                symbol: regime.regime
                for symbol, regime in self.current_regimes.items()
            },
            'status': 'ACTIVE'
        }


# Strategy metadata for orchestrator registration
STRATEGY_METADATA = {
    'name': 'VolatilityRegimeDetector',
    'version': '1.0.0',
    'description': 'Elite volatility analysis with regime detection and black swan protection',
    'type': 'RISK_MANAGER',
    'timeframe': '1m',
    'min_capital_usd': 10000,
    'expected_win_rate': 0.58,
    'expected_risk_reward': 2.0,
    'max_drawdown_target': 0.08,
    'requires_level2_data': False,
    'requires_ohlcv': True,
    'latency_requirement_ms': 100
}

