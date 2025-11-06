"""
Unit tests for enhancement modules
"""
import pytest
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.strategies.enhancements.ml_regime_classifier import (
    MLRegimeClassifier, RegimeFeatures
)
from src.strategies.enhancements.position_sizer import (
    AdvancedPositionSizer, PositionSizeRecommendation
)
from src.strategies.enhancements.signal_scorer import SignalScorer, SignalQuality


class TestMLRegimeClassifier:
    """Test ML regime classifier"""
    
    def test_initialization(self):
        """Test classifier initializes correctly"""
        classifier = MLRegimeClassifier()
        assert classifier is not None
        assert classifier.is_trained == False
    
    def test_simple_classification(self):
        """Test fallback rule-based classification"""
        classifier = MLRegimeClassifier()
        
        # Low volatility
        features = RegimeFeatures(
            realized_vol_1h=0.10, realized_vol_4h=0.10, realized_vol_24h=0.10,
            vol_of_vol=0.02, volume_1h=1000000, volume_4h=3000000,
            volume_24h=10000000, volume_ratio=1.0, returns_1h=0.01,
            returns_4h=0.02, returns_24h=0.03, price_range_1h=0.01,
            spread_bps=5.0, order_book_imbalance=0.1, depth_imbalance=0.1,
            trade_aggression=0.5, large_trade_frequency=0.1
        )
        
        regime, confidence = classifier.predict(features)
        assert regime == 0  # LOW_VOLATILITY_TRENDING
        assert 0 <= confidence <= 1
    
    def test_regime_names(self):
        """Test regime name mapping"""
        classifier = MLRegimeClassifier()
        assert classifier.get_regime_name(0) == "LOW_VOLATILITY_TRENDING"
        assert classifier.get_regime_name(1) == "MEDIUM_VOLATILITY_RANGING"
        assert classifier.get_regime_name(2) == "HIGH_VOLATILITY_TRENDING"
        assert classifier.get_regime_name(3) == "EXTREME_VOLATILITY_CHAOS"
    
    def test_feature_array_conversion(self):
        """Test feature conversion to numpy array"""
        features = RegimeFeatures(
            realized_vol_1h=0.25, realized_vol_4h=0.30, realized_vol_24h=0.35,
            vol_of_vol=0.05, volume_1h=1000000, volume_4h=3500000,
            volume_24h=10000000, volume_ratio=1.2, returns_1h=0.02,
            returns_4h=0.05, returns_24h=0.08, price_range_1h=0.015,
            spread_bps=5.0, order_book_imbalance=0.3, depth_imbalance=0.2,
            trade_aggression=0.65, large_trade_frequency=0.15
        )
        
        arr = features.to_array()
        assert isinstance(arr, np.ndarray)
        assert len(arr) == 17


class TestPositionSizer:
    """Test position sizing"""
    
    def test_initialization(self):
        """Test sizer initializes correctly"""
        sizer = AdvancedPositionSizer(
            portfolio_value=100000,
            max_risk_per_trade_pct=0.02
        )
        assert sizer.portfolio_value == 100000
        assert sizer.max_risk_per_trade_pct == 0.02
    
    def test_kelly_position(self):
        """Test Kelly Criterion sizing"""
        sizer = AdvancedPositionSizer(portfolio_value=100000)
        
        position = sizer.calculate_kelly_position(
            symbol="BTCUSDT",
            win_rate=0.60,
            avg_win=100,
            avg_loss=50,
            current_price=45000,
            stop_loss_distance_pct=0.02
        )
        
        assert isinstance(position, PositionSizeRecommendation)
        assert position.symbol == "BTCUSDT"
        assert position.recommended_size_usd > 0
        assert position.max_loss_usd <= 100000 * 0.02  # Max 2% risk
        assert position.sizing_method == 'KELLY_CRITERION'
    
    def test_volatility_position(self):
        """Test volatility-based sizing"""
        sizer = AdvancedPositionSizer(portfolio_value=100000)
        
        position = sizer.calculate_volatility_position(
            symbol="BTCUSDT",
            current_price=45000,
            realized_volatility=0.30,
            stop_loss_distance_pct=0.015
        )
        
        assert position.sizing_method == 'VOLATILITY_BASED'
        assert position.recommended_size_usd > 0
        assert 0 <= position.risk_percent <= 0.02
    
    def test_fixed_fractional(self):
        """Test fixed fractional sizing"""
        sizer = AdvancedPositionSizer(portfolio_value=100000)
        
        position = sizer.calculate_fixed_fractional_position(
            symbol="BTCUSDT",
            current_price=45000,
            allocation_pct=0.10,  # 10% of portfolio
            stop_loss_distance_pct=0.02
        )
        
        assert position.sizing_method == 'FIXED_FRACTIONAL'
        assert position.recommended_size_usd == 10000  # 10% of 100k
    
    def test_portfolio_update(self):
        """Test portfolio value update"""
        sizer = AdvancedPositionSizer(portfolio_value=100000)
        sizer.update_portfolio_value(105000)
        assert sizer.portfolio_value == 105000


class TestSignalScorer:
    """Test signal scoring"""
    
    def test_initialization(self):
        """Test scorer initializes correctly"""
        scorer = SignalScorer(min_score_to_trade=70.0)
        assert scorer.min_score_to_trade == 70.0
    
    def test_excellent_signal(self):
        """Test scoring of excellent signal"""
        scorer = SignalScorer(min_score_to_trade=70.0)
        
        score = scorer.score_signal(
            price_near_support_resistance=True,
            technical_indicators_aligned=True,
            pattern_detected=True,
            whale_activity_present=True,
            volume_above_average=3.0,
            order_book_imbalance=0.8,
            volatility_regime='MEDIUM',
            volatility_percentile=40,
            trend_strength=0.85,
            momentum_acceleration=0.6,
            risk_reward_ratio=3.0,
            stop_loss_distance_pct=0.008,
            market_liquidity_score=0.90,
            spread_quality=0.95
        )
        
        assert score.total_score >= 85  # Should be excellent
        assert score.quality == SignalQuality.EXCELLENT
        assert score.trade_recommended == True
        assert len(score.strengths) > 0
    
    def test_poor_signal(self):
        """Test scoring of poor signal"""
        scorer = SignalScorer(min_score_to_trade=70.0)
        
        score = scorer.score_signal(
            price_near_support_resistance=False,
            technical_indicators_aligned=False,
            pattern_detected=False,
            whale_activity_present=False,
            volume_above_average=0.5,
            order_book_imbalance=0.1,
            volatility_regime='EXTREME',
            volatility_percentile=95,
            trend_strength=0.2,
            momentum_acceleration=-0.3,
            risk_reward_ratio=0.8,
            stop_loss_distance_pct=0.025,
            market_liquidity_score=0.40,
            spread_quality=0.50
        )
        
        assert score.total_score < 60  # Should be poor
        assert score.quality == SignalQuality.POOR
        assert score.trade_recommended == False
        assert len(score.weaknesses) > 0
    
    def test_component_scores(self):
        """Test individual component scores"""
        scorer = SignalScorer()
        
        score = scorer.score_signal(
            price_near_support_resistance=True,
            technical_indicators_aligned=True,
            pattern_detected=True,
            whale_activity_present=True,
            volume_above_average=2.0,
            order_book_imbalance=0.7,
            volatility_regime='LOW',
            volatility_percentile=30,
            trend_strength=0.75,
            momentum_acceleration=0.5,
            risk_reward_ratio=2.5,
            stop_loss_distance_pct=0.010,
            market_liquidity_score=0.80,
            spread_quality=0.85
        )
        
        # All scores should be 0-100
        assert 0 <= score.technical_score <= 100
        assert 0 <= score.volume_score <= 100
        assert 0 <= score.volatility_score <= 100
        assert 0 <= score.momentum_score <= 100
        assert 0 <= score.risk_reward_score <= 100
        assert 0 <= score.timing_score <= 100


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

