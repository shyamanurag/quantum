"""
Multi-Factor Signal Scoring System

Scores signals based on multiple factors for trade quality assessment.
"""
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SignalQuality(Enum):
    """Signal quality classification"""
    EXCELLENT = "excellent"  # >90%
    GOOD = "good"  # 75-90%
    FAIR = "fair"  # 60-75%
    POOR = "poor"  # <60%


@dataclass
class SignalScore:
    """Comprehensive signal score"""
    total_score: float  # 0-100
    quality: SignalQuality
    
    # Component scores (0-100 each)
    technical_score: float
    volume_score: float
    volatility_score: float
    momentum_score: float
    risk_reward_score: float
    timing_score: float
    
    # Confidence
    confidence: float
    trade_recommended: bool
    
    # Explanation
    strengths: List[str]
    weaknesses: List[str]


class SignalScorer:
    """
    Scores trading signals using multi-factor analysis.
    
    Factors:
    1. Technical (30%): price action, patterns, indicators
    2. Volume (20%): order flow, whale activity, volume profile
    3. Volatility (15%): regime, stability, predictability
    4. Momentum (15%): trend strength, acceleration
    5. Risk/Reward (10%): potential profit vs risk
    6. Timing (10%): market conditions, session times
    """
    
    def __init__(
        self,
        min_score_to_trade: float = 70.0,
        weights: Optional[Dict[str, float]] = None
    ):
        self.min_score_to_trade = min_score_to_trade
        
        # Default weights
        self.weights = weights or {
            'technical': 0.30,
            'volume': 0.20,
            'volatility': 0.15,
            'momentum': 0.15,
            'risk_reward': 0.10,
            'timing': 0.10
        }
        
        logger.info(f"SignalScorer initialized: min_score={min_score_to_trade}")
    
    def score_signal(
        self,
        # Technical factors
        price_near_support_resistance: bool,
        technical_indicators_aligned: bool,
        pattern_detected: bool,
        
        # Volume factors
        whale_activity_present: bool,
        volume_above_average: float,  # ratio
        order_book_imbalance: float,  # -1 to +1
        
        # Volatility factors
        volatility_regime: str,  # LOW, MEDIUM, HIGH, EXTREME
        volatility_percentile: float,  # 0-100
        
        # Momentum factors
        trend_strength: float,  # 0-1
        momentum_acceleration: float,  # -1 to +1
        
        # Risk/reward factors
        risk_reward_ratio: float,
        stop_loss_distance_pct: float,
        
        # Timing factors
        market_liquidity_score: float,  # 0-1
        spread_quality: float  # 0-1 (tight = 1)
    ) -> SignalScore:
        """Score a trading signal"""
        
        # 1. Technical Score (0-100)
        technical_score = self._score_technical(
            price_near_support_resistance,
            technical_indicators_aligned,
            pattern_detected
        )
        
        # 2. Volume Score (0-100)
        volume_score = self._score_volume(
            whale_activity_present,
            volume_above_average,
            order_book_imbalance
        )
        
        # 3. Volatility Score (0-100)
        volatility_score = self._score_volatility(
            volatility_regime,
            volatility_percentile
        )
        
        # 4. Momentum Score (0-100)
        momentum_score = self._score_momentum(
            trend_strength,
            momentum_acceleration
        )
        
        # 5. Risk/Reward Score (0-100)
        risk_reward_score = self._score_risk_reward(
            risk_reward_ratio,
            stop_loss_distance_pct
        )
        
        # 6. Timing Score (0-100)
        timing_score = self._score_timing(
            market_liquidity_score,
            spread_quality
        )
        
        # Calculate weighted total
        total_score = (
            technical_score * self.weights['technical'] +
            volume_score * self.weights['volume'] +
            volatility_score * self.weights['volatility'] +
            momentum_score * self.weights['momentum'] +
            risk_reward_score * self.weights['risk_reward'] +
            timing_score * self.weights['timing']
        )
        
        # Determine quality
        if total_score >= 90:
            quality = SignalQuality.EXCELLENT
        elif total_score >= 75:
            quality = SignalQuality.GOOD
        elif total_score >= 60:
            quality = SignalQuality.FAIR
        else:
            quality = SignalQuality.POOR
        
        # Calculate confidence (based on score consistency)
        scores = [technical_score, volume_score, volatility_score,
                 momentum_score, risk_reward_score, timing_score]
        score_std = np.std(scores)
        confidence = max(0.5, min(1.0, 1.0 - (score_std / 50.0)))
        
        # Trade recommendation
        trade_recommended = total_score >= self.min_score_to_trade
        
        # Identify strengths and weaknesses
        strengths, weaknesses = self._analyze_components(
            technical_score, volume_score, volatility_score,
            momentum_score, risk_reward_score, timing_score
        )
        
        return SignalScore(
            total_score=total_score,
            quality=quality,
            technical_score=technical_score,
            volume_score=volume_score,
            volatility_score=volatility_score,
            momentum_score=momentum_score,
            risk_reward_score=risk_reward_score,
            timing_score=timing_score,
            confidence=confidence,
            trade_recommended=trade_recommended,
            strengths=strengths,
            weaknesses=weaknesses
        )
    
    def _score_technical(
        self,
        price_near_sr: bool,
        indicators_aligned: bool,
        pattern_detected: bool
    ) -> float:
        """Score technical factors"""
        score = 50.0  # Base score
        
        if price_near_sr:
            score += 20
        if indicators_aligned:
            score += 20
        if pattern_detected:
            score += 10
        
        return min(100.0, score)
    
    def _score_volume(
        self,
        whale_activity: bool,
        volume_ratio: float,
        imbalance: float
    ) -> float:
        """Score volume factors"""
        score = 40.0  # Base
        
        if whale_activity:
            score += 30
        
        # Volume ratio scoring
        if volume_ratio > 2.0:
            score += 20
        elif volume_ratio > 1.5:
            score += 10
        
        # Imbalance scoring
        if abs(imbalance) > 0.6:
            score += 10
        
        return min(100.0, score)
    
    def _score_volatility(
        self,
        regime: str,
        percentile: float
    ) -> float:
        """Score volatility factors"""
        if regime == 'LOW':
            base = 80  # Prefer low vol
        elif regime == 'MEDIUM':
            base = 70
        elif regime == 'HIGH':
            base = 50
        else:  # EXTREME
            base = 20  # Avoid extreme vol
        
        # Adjust for percentile
        if percentile < 50:
            adjustment = 10
        elif percentile > 80:
            adjustment = -20
        else:
            adjustment = 0
        
        return max(0, min(100, base + adjustment))
    
    def _score_momentum(
        self,
        trend_strength: float,
        acceleration: float
    ) -> float:
        """Score momentum factors"""
        score = 50.0
        
        # Trend strength (0-1)
        score += trend_strength * 30
        
        # Acceleration
        if acceleration > 0.5:
            score += 20
        elif acceleration > 0.2:
            score += 10
        elif acceleration < -0.2:
            score -= 10
        
        return max(0, min(100, score))
    
    def _score_risk_reward(
        self,
        rr_ratio: float,
        stop_distance: float
    ) -> float:
        """Score risk/reward"""
        score = 30.0
        
        # R/R ratio
        if rr_ratio >= 3.0:
            score += 50
        elif rr_ratio >= 2.0:
            score += 30
        elif rr_ratio >= 1.5:
            score += 20
        else:
            score += 10
        
        # Stop distance
        if stop_distance < 0.005:  # <0.5%
            score += 20
        elif stop_distance < 0.01:  # <1%
            score += 10
        
        return min(100, score)
    
    def _score_timing(
        self,
        liquidity: float,
        spread: float
    ) -> float:
        """Score timing factors"""
        score = 50.0
        
        score += liquidity * 30
        score += spread * 20
        
        return min(100, score)
    
    def _analyze_components(
        self,
        technical: float,
        volume: float,
        volatility: float,
        momentum: float,
        risk_reward: float,
        timing: float
    ) -> Tuple[List[str], List[str]]:
        """Identify strengths and weaknesses"""
        strengths = []
        weaknesses = []
        
        components = {
            'Technical': technical,
            'Volume': volume,
            'Volatility': volatility,
            'Momentum': momentum,
            'Risk/Reward': risk_reward,
            'Timing': timing
        }
        
        for name, score in components.items():
            if score >= 80:
                strengths.append(f"Strong {name} ({score:.0f}/100)")
            elif score < 50:
                weaknesses.append(f"Weak {name} ({score:.0f}/100)")
        
        return strengths, weaknesses



