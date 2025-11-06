"""
Machine Learning Regime Classifier

Uses ensemble learning to classify market regimes with high accuracy.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


@dataclass
class RegimeFeatures:
    """Feature vector for regime classification"""
    # Volatility features
    realized_vol_1h: float
    realized_vol_4h: float
    realized_vol_24h: float
    vol_of_vol: float
    
    # Volume features
    volume_1h: float
    volume_4h: float
    volume_24h: float
    volume_ratio: float  # current / average
    
    # Price features
    returns_1h: float
    returns_4h: float
    returns_24h: float
    price_range_1h: float
    
    # Order book features
    spread_bps: float
    order_book_imbalance: float
    depth_imbalance: float
    
    # Market microstructure
    trade_aggression: float  # % of market orders
    large_trade_frequency: float
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array for ML"""
        return np.array([
            self.realized_vol_1h, self.realized_vol_4h, self.realized_vol_24h,
            self.vol_of_vol, self.volume_1h, self.volume_4h, self.volume_24h,
            self.volume_ratio, self.returns_1h, self.returns_4h, self.returns_24h,
            self.price_range_1h, self.spread_bps, self.order_book_imbalance,
            self.depth_imbalance, self.trade_aggression, self.large_trade_frequency
        ])


class MLRegimeClassifier:
    """
    Ensemble ML classifier for market regimes.
    
    Regimes:
    0 = LOW_VOLATILITY_TRENDING
    1 = MEDIUM_VOLATILITY_RANGING
    2 = HIGH_VOLATILITY_TRENDING
    3 = EXTREME_VOLATILITY_CHAOS
    """
    
    def __init__(self):
        self.rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.gb_model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
        self.scaler = StandardScaler()
        
        self.is_trained = False
        self.feature_history: deque = deque(maxlen=1000)
        self.regime_history: deque = deque(maxlen=1000)
        
        logger.info("MLRegimeClassifier initialized (untrained)")
    
    def train(self, features: List[RegimeFeatures], labels: List[int]):
        """
        Train the ensemble on historical data.
        
        Args:
            features: List of feature vectors
            labels: True regime labels (0-3)
        """
        if len(features) < 100:
            logger.warning("Insufficient training data (<100 samples)")
            return
        
        # Convert to numpy arrays
        X = np.array([f.to_array() for f in features])
        y = np.array(labels)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train models
        self.rf_model.fit(X_scaled, y)
        self.gb_model.fit(X_scaled, y)
        
        self.is_trained = True
        logger.info(f"MLRegimeClassifier trained on {len(features)} samples")
    
    def predict(self, features: RegimeFeatures) -> Tuple[int, float]:
        """
        Predict current regime with confidence.
        
        Returns:
            (regime_id, confidence)
        """
        if not self.is_trained:
            # Fallback to simple rule-based
            return self._simple_classification(features)
        
        # Scale features
        X = features.to_array().reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        # Get predictions from both models
        rf_pred = self.rf_model.predict(X_scaled)[0]
        rf_proba = self.rf_model.predict_proba(X_scaled)[0]
        
        gb_pred = self.gb_model.predict(X_scaled)[0]
        gb_proba = self.gb_model.predict_proba(X_scaled)[0]
        
        # Ensemble: weighted average
        ensemble_proba = 0.6 * rf_proba + 0.4 * gb_proba
        regime = np.argmax(ensemble_proba)
        confidence = ensemble_proba[regime]
        
        # Store in history
        self.feature_history.append(features)
        self.regime_history.append(regime)
        
        return int(regime), float(confidence)
    
    def _simple_classification(self, features: RegimeFeatures) -> Tuple[int, float]:
        """Fallback rule-based classification"""
        vol = features.realized_vol_24h
        
        if vol < 0.15:
            return (0, 0.7)  # LOW_VOLATILITY_TRENDING
        elif vol < 0.35:
            return (1, 0.7)  # MEDIUM_VOLATILITY_RANGING
        elif vol < 0.60:
            return (2, 0.7)  # HIGH_VOLATILITY_TRENDING
        else:
            return (3, 0.7)  # EXTREME_VOLATILITY_CHAOS
    
    def get_regime_name(self, regime_id: int) -> str:
        """Get human-readable regime name"""
        names = {
            0: "LOW_VOLATILITY_TRENDING",
            1: "MEDIUM_VOLATILITY_RANGING",
            2: "HIGH_VOLATILITY_TRENDING",
            3: "EXTREME_VOLATILITY_CHAOS"
        }
        return names.get(regime_id, "UNKNOWN")
    
    def get_regime_transition_probability(self, current_regime: int, target_regime: int) -> float:
        """
        Calculate probability of transitioning from current to target regime.
        Based on historical transitions.
        """
        if len(self.regime_history) < 50:
            return 0.25  # Uniform prior
        
        # Count transitions
        transitions = 0
        total = 0
        
        for i in range(1, len(self.regime_history)):
            if self.regime_history[i-1] == current_regime:
                total += 1
                if self.regime_history[i] == target_regime:
                    transitions += 1
        
        if total == 0:
            return 0.25
        
        return transitions / total



