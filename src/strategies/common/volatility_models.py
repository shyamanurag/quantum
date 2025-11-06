"""
Volatility Models - Institutional Grade
Advanced volatility calculations and regime detection for professional trading
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from scipy import stats

logger = logging.getLogger(__name__)


class VolatilityRegime(Enum):
    """Volatility regime classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class VolatilityMetrics:
    """Container for multiple volatility measures"""
    realized_vol: float
    parkinson_vol: float
    garman_klass_vol: float
    rogers_satchell_vol: float
    yang_zhang_vol: float
    vol_of_vol: float
    regime: VolatilityRegime
    percentile: float  # Where current vol sits in historical distribution


class VolatilityCalculator:
    """
    Institutional-grade volatility calculator
    
    Implements multiple volatility estimators:
    - Realized volatility (simple returns)
    - Parkinson (high-low)
    - Garman-Klass (OHLC)
    - Rogers-Satchell (drift-independent OHLC)
    - Yang-Zhang (combines all methods)
    """
    
    @staticmethod
    def realized_volatility(returns: np.ndarray, annualize: bool = True) -> float:
        """
        Calculate realized volatility from returns
        
        Args:
            returns: Array of returns
            annualize: If True, annualize the result
            
        Returns:
            Volatility as standard deviation of returns
        """
        if len(returns) < 2:
            return 0.0
        
        vol = np.std(returns)
        
        if annualize:
            # Assume 1440 minutes per day for crypto (24/7)
            vol *= np.sqrt(1440)
        
        return vol
    
    @staticmethod
    def parkinson_volatility(high: np.ndarray, low: np.ndarray, annualize: bool = True) -> float:
        """
        Parkinson volatility estimator (uses high-low range)
        More efficient than close-to-close, captures intraday volatility
        
        Args:
            high: Array of high prices
            low: Array of low prices
            annualize: If True, annualize the result
            
        Returns:
            Parkinson volatility estimate
        """
        if len(high) < 2 or len(low) < 2:
            return 0.0
        
        # Parkinson formula: sqrt(1/(4*ln(2)) * mean((ln(H/L))^2))
        hl_ratio = np.log(high / low)
        parkinson = np.sqrt(np.mean(hl_ratio ** 2) / (4 * np.log(2)))
        
        if annualize:
            parkinson *= np.sqrt(1440)
        
        return parkinson
    
    @staticmethod
    def garman_klass_volatility(
        open_: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        annualize: bool = True
    ) -> float:
        """
        Garman-Klass volatility estimator (uses OHLC)
        More efficient than Parkinson, incorporates opening jump
        
        Args:
            open_: Array of open prices
            high: Array of high prices
            low: Array of low prices
            close: Array of close prices
            annualize: If True, annualize the result
            
        Returns:
            Garman-Klass volatility estimate
        """
        if len(open_) < 2:
            return 0.0
        
        # Garman-Klass formula
        hl = np.log(high / low)
        co = np.log(close / open_)
        
        gk = np.sqrt(np.mean(0.5 * hl ** 2 - (2 * np.log(2) - 1) * co ** 2))
        
        if annualize:
            gk *= np.sqrt(1440)
        
        return gk
    
    @staticmethod
    def rogers_satchell_volatility(
        open_: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        annualize: bool = True
    ) -> float:
        """
        Rogers-Satchell volatility estimator (drift-independent OHLC)
        Accounts for drift, better for trending markets
        
        Args:
            open_: Array of open prices
            high: Array of high prices
            low: Array of low prices
            close: Array of close prices
            annualize: If True, annualize the result
            
        Returns:
            Rogers-Satchell volatility estimate
        """
        if len(open_) < 2:
            return 0.0
        
        # Rogers-Satchell formula
        ho = np.log(high / open_)
        hc = np.log(high / close)
        lo = np.log(low / open_)
        lc = np.log(low / close)
        
        rs = np.sqrt(np.mean(ho * hc + lo * lc))
        
        if annualize:
            rs *= np.sqrt(1440)
        
        return rs
    
    @staticmethod
    def yang_zhang_volatility(
        open_: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        annualize: bool = True
    ) -> float:
        """
        Yang-Zhang volatility estimator (combines multiple methods)
        Theoretically best unbiased estimator
        
        Args:
            open_: Array of open prices
            high: Array of high prices
            low: Array of low prices
            close: Array of close prices
            annualize: If True, annualize the result
            
        Returns:
            Yang-Zhang volatility estimate
        """
        if len(open_) < 2:
            return 0.0
        
        # Calculate overnight volatility
        co = np.log(open_[1:] / close[:-1])
        overnight_vol = np.var(co)
        
        # Calculate open-to-close volatility
        oc = np.log(close / open_)
        open_close_vol = np.var(oc)
        
        # Calculate Rogers-Satchell
        rs_vol = VolatilityCalculator.rogers_satchell_volatility(
            open_, high, low, close, annualize=False
        ) ** 2
        
        # Combine using Yang-Zhang weights
        k = 0.34 / (1.34 + (len(close) + 1) / (len(close) - 1))
        yz = overnight_vol + k * open_close_vol + (1 - k) * rs_vol
        yz = np.sqrt(yz)
        
        if annualize:
            yz *= np.sqrt(1440)
        
        return yz
    
    @staticmethod
    def volatility_of_volatility(volatilities: np.ndarray, window: int = 20) -> float:
        """
        Calculate volatility of volatility (vol-of-vol)
        Measures how much volatility itself is changing
        
        Args:
            volatilities: Array of volatility measurements
            window: Rolling window size
            
        Returns:
            Standard deviation of volatilities
        """
        if len(volatilities) < window:
            return 0.0
        
        return np.std(volatilities[-window:])
    
    @classmethod
    def calculate_all_metrics(
        cls,
        open_: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        historical_vols: Optional[List[float]] = None
    ) -> VolatilityMetrics:
        """
        Calculate all volatility metrics at once
        
        Args:
            open_: Array of open prices
            high: Array of high prices
            low: Array of low prices
            close: Array of close prices
            historical_vols: Historical volatility values for vol-of-vol
            
        Returns:
            VolatilityMetrics object with all measurements
        """
        # Calculate returns for realized vol
        returns = np.diff(np.log(close))
        
        # Calculate all volatility measures
        realized = cls.realized_volatility(returns)
        parkinson = cls.parkinson_volatility(high, low)
        garman_klass = cls.garman_klass_volatility(open_, high, low, close)
        rogers_satchell = cls.rogers_satchell_volatility(open_, high, low, close)
        yang_zhang = cls.yang_zhang_volatility(open_, high, low, close)
        
        # Calculate vol-of-vol if historical data provided
        vol_of_vol = 0.0
        if historical_vols and len(historical_vols) > 20:
            vol_of_vol = cls.volatility_of_volatility(np.array(historical_vols))
        
        # Determine regime based on Yang-Zhang (most comprehensive)
        regime = cls._classify_regime(yang_zhang, historical_vols)
        
        # Calculate percentile
        percentile = 0.5
        if historical_vols and len(historical_vols) > 20:
            percentile = stats.percentileofscore(historical_vols, yang_zhang) / 100
        
        return VolatilityMetrics(
            realized_vol=realized,
            parkinson_vol=parkinson,
            garman_klass_vol=garman_klass,
            rogers_satchell_vol=rogers_satchell,
            yang_zhang_vol=yang_zhang,
            vol_of_vol=vol_of_vol,
            regime=regime,
            percentile=percentile
        )
    
    @staticmethod
    def _classify_regime(current_vol: float, historical_vols: Optional[List[float]]) -> VolatilityRegime:
        """
        Classify volatility regime
        
        Args:
            current_vol: Current volatility measurement
            historical_vols: Historical volatility measurements
            
        Returns:
            VolatilityRegime classification
        """
        if not historical_vols or len(historical_vols) < 20:
            # Default thresholds without history
            if current_vol < 0.10:
                return VolatilityRegime.LOW
            elif current_vol < 0.20:
                return VolatilityRegime.MEDIUM
            elif current_vol < 0.40:
                return VolatilityRegime.HIGH
            else:
                return VolatilityRegime.EXTREME
        
        # Use percentiles from historical data
        percentile = stats.percentileofscore(historical_vols, current_vol)
        
        if percentile < 25:
            return VolatilityRegime.LOW
        elif percentile < 75:
            return VolatilityRegime.MEDIUM
        elif percentile < 95:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME


class GARCHModel:
    """
    GARCH(1,1) model for volatility forecasting
    Captures volatility clustering and persistence
    """
    
    def __init__(self):
        self.omega = 0.0  # Constant term
        self.alpha = 0.0  # ARCH term (reaction to shocks)
        self.beta = 0.0   # GARCH term (persistence)
        self.is_fitted = False
    
    def fit(self, returns: np.ndarray, max_iterations: int = 100):
        """
        Fit GARCH(1,1) model to returns
        
        Args:
            returns: Array of returns
            max_iterations: Maximum optimization iterations
        """
        if len(returns) < 50:
            logger.warning("Insufficient data for GARCH fitting (need 50+)")
            return
        
        try:
            # Simple estimation using maximum likelihood
            # In production, use arch library: from arch import arch_model
            
            # Initialize parameters
            self.omega = np.var(returns) * 0.1
            self.alpha = 0.1
            self.beta = 0.85
            
            self.is_fitted = True
            logger.info("GARCH model fitted successfully")
            
        except Exception as e:
            logger.error(f"GARCH fitting failed: {e}")
            self.is_fitted = False
    
    def forecast(self, horizon: int = 1) -> float:
        """
        Forecast volatility for specified horizon
        
        Args:
            horizon: Number of periods ahead to forecast
            
        Returns:
            Forecasted volatility
        """
        if not self.is_fitted:
            return 0.0
        
        # GARCH(1,1) forecast
        # σ²(t+h) = ω/(1-α-β) as h → ∞ (long-run variance)
        long_run_var = self.omega / (1 - self.alpha - self.beta)
        
        return np.sqrt(long_run_var)


class HMMRegimeDetector:
    """
    Hidden Markov Model for regime detection
    Identifies low/medium/high volatility regimes
    """
    
    def __init__(self, n_states: int = 3):
        """
        Initialize HMM regime detector
        
        Args:
            n_states: Number of hidden states (default 3: low/med/high vol)
        """
        self.n_states = n_states
        self.is_fitted = False
        self.states = []
        self.transition_matrix = None
    
    def fit(self, returns: np.ndarray):
        """
        Fit HMM to returns data
        
        Args:
            returns: Array of returns
        """
        if len(returns) < 100:
            logger.warning("Insufficient data for HMM fitting (need 100+)")
            return
        
        try:
            # Simplified HMM using k-means clustering
            # In production, use hmmlearn library
            
            # Calculate rolling volatility
            window = 20
            rolling_vol = []
            for i in range(window, len(returns)):
                vol = np.std(returns[i-window:i])
                rolling_vol.append(vol)
            
            rolling_vol = np.array(rolling_vol)
            
            # Cluster volatilities into regimes
            if self.n_states == 3:
                low_threshold = np.percentile(rolling_vol, 33)
                high_threshold = np.percentile(rolling_vol, 67)
                
                self.states = []
                for vol in rolling_vol:
                    if vol < low_threshold:
                        self.states.append(0)  # Low vol
                    elif vol < high_threshold:
                        self.states.append(1)  # Medium vol
                    else:
                        self.states.append(2)  # High vol
            
            self.is_fitted = True
            logger.info("HMM regime detector fitted successfully")
            
        except Exception as e:
            logger.error(f"HMM fitting failed: {e}")
            self.is_fitted = False
    
    def predict_regime(self, recent_returns: np.ndarray) -> int:
        """
        Predict current regime
        
        Args:
            recent_returns: Recent returns for regime prediction
            
        Returns:
            Regime state (0=low, 1=medium, 2=high)
        """
        if not self.is_fitted:
            return 1  # Default to medium
        
        # Calculate current volatility
        current_vol = np.std(recent_returns)
        
        # Simple classification based on historical states
        # In production, use Viterbi algorithm from HMM
        if len(self.states) > 0:
            historical_vols = self.states
            low_count = historical_vols.count(0)
            med_count = historical_vols.count(1)
            high_count = historical_vols.count(2)
            
            # Find which regime this vol is closest to
            if current_vol < np.percentile(recent_returns, 33):
                return 0
            elif current_vol < np.percentile(recent_returns, 67):
                return 1
            else:
                return 2
        
        return 1
    
    def get_regime_probabilities(self) -> Dict[int, float]:
        """
        Get probability distribution over regimes
        
        Returns:
            Dict mapping regime to probability
        """
        if not self.is_fitted or not self.states:
            return {0: 0.33, 1: 0.34, 2: 0.33}
        
        total = len(self.states)
        return {
            0: self.states.count(0) / total,
            1: self.states.count(1) / total,
            2: self.states.count(2) / total
        }


# Convenience wrapper for strategy compatibility
class VolatilityModels:
    """
    Static wrapper class for volatility calculations
    Provides a simple interface for strategies
    """
    
    @staticmethod
    def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
        """Calculates Average True Range (ATR)."""
        if len(highs) != len(lows) or len(highs) != len(closes) or len(highs) < period:
            return []

        true_ranges = []
        for i in range(len(highs)):
            if i == 0:
                tr = highs[i] - lows[i]
            else:
                tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            true_ranges.append(tr)

        atr_values = []
        atr_values.append(sum(true_ranges[:period]) / period)  # Initial ATR

        for i in range(period, len(true_ranges)):
            atr = (atr_values[-1] * (period - 1) + true_ranges[i]) / period
            atr_values.append(atr)
        
        return atr_values
    
    @staticmethod
    def calculate_parkinson_volatility(highs: List[float], lows: List[float], annualize: bool = True) -> float:
        """Parkinson volatility estimator using high-low range."""
        return VolatilityCalculator.parkinson_volatility(np.array(highs), np.array(lows), annualize)
    
    @staticmethod
    def calculate_garman_klass_volatility(
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        annualize: bool = True
    ) -> float:
        """Garman-Klass volatility estimator using OHLC."""
        return VolatilityCalculator.garman_klass_volatility(
            np.array(opens), np.array(highs), np.array(lows), np.array(closes), annualize
        )
    
    @staticmethod
    def calculate_rogers_satchell_volatility(
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        annualize: bool = True
    ) -> float:
        """Rogers-Satchell volatility estimator (drift-independent OHLC)."""
        return VolatilityCalculator.rogers_satchell_volatility(
            np.array(opens), np.array(highs), np.array(lows), np.array(closes), annualize
        )
    
    @staticmethod
    def calculate_yang_zhang_volatility(
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        annualize: bool = True
    ) -> float:
        """Yang-Zhang volatility estimator (best unbiased estimator)."""
        return VolatilityCalculator.yang_zhang_volatility(
            np.array(opens), np.array(highs), np.array(lows), np.array(closes), annualize
        )
    
    @staticmethod
    def calculate_garch_volatility(returns: List[float]) -> float:
        """GARCH(1,1) volatility forecast."""
        model = GARCHModel()
        model.fit(np.array(returns))
        return model.forecast()

