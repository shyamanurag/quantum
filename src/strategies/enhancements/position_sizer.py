"""
Advanced Position Sizing Calculator

Kelly Criterion, volatility-based, and risk parity position sizing.
"""
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PositionSizeRecommendation:
    """Position size recommendation with risk metrics"""
    symbol: str
    recommended_size_usd: float
    recommended_size_base: float  # in base currency
    max_loss_usd: float
    risk_percent: float
    sizing_method: str
    confidence: float
    leverage: float = 1.0


class AdvancedPositionSizer:
    """
    Institutional-grade position sizing.
    
    Methods:
    1. Kelly Criterion (optimal bet sizing)
    2. Volatility-based (constant risk)
    3. Risk parity (equal risk contribution)
    4. Fixed fractional (% of portfolio)
    """
    
    def __init__(
        self,
        portfolio_value: float,
        max_risk_per_trade_pct: float = 0.02,  # 2% max risk
        target_volatility: float = 0.15,  # 15% annualized
        kelly_fraction: float = 0.25  # Quarter Kelly (conservative)
    ):
        self.portfolio_value = portfolio_value
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.target_volatility = target_volatility
        self.kelly_fraction = kelly_fraction
        
        logger.info(
            f"AdvancedPositionSizer initialized: "
            f"portfolio=${portfolio_value:,.0f}, max_risk={max_risk_per_trade_pct:.1%}"
        )
    
    def calculate_kelly_position(
        self,
        symbol: str,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        current_price: float,
        stop_loss_distance_pct: float
    ) -> PositionSizeRecommendation:
        """
        Kelly Criterion position sizing.
        
        Formula: f = (bp - q) / b
        where:
        - f = fraction to bet
        - b = odds (avg_win / avg_loss)
        - p = win probability
        - q = loss probability (1 - p)
        """
        if win_rate <= 0 or win_rate >= 1:
            win_rate = 0.5  # Default to 50%
        
        if avg_loss <= 0:
            logger.error("avg_loss must be positive")
            return self._fallback_sizing(symbol, current_price, stop_loss_distance_pct)
        
        b = abs(avg_win / avg_loss)  # Odds
        p = win_rate
        q = 1 - p
        
        # Kelly formula
        kelly_f = (b * p - q) / b
        
        # Apply Kelly fraction (conservative)
        kelly_f = kelly_f * self.kelly_fraction
        
        # Constrain to max risk
        kelly_f = max(0, min(kelly_f, self.max_risk_per_trade_pct))
        
        # Calculate position size
        risk_amount = self.portfolio_value * kelly_f
        position_size_usd = risk_amount / stop_loss_distance_pct
        position_size_base = position_size_usd / current_price
        
        return PositionSizeRecommendation(
            symbol=symbol,
            recommended_size_usd=position_size_usd,
            recommended_size_base=position_size_base,
            max_loss_usd=risk_amount,
            risk_percent=kelly_f,
            sizing_method='KELLY_CRITERION',
            confidence=0.9
        )
    
    def calculate_volatility_position(
        self,
        symbol: str,
        current_price: float,
        realized_volatility: float,
        stop_loss_distance_pct: float
    ) -> PositionSizeRecommendation:
        """
        Volatility-based position sizing (constant risk).
        
        Size inversely proportional to volatility.
        """
        if realized_volatility <= 0:
            realized_volatility = 0.20  # Default 20%
        
        # Target position volatility
        vol_scalar = self.target_volatility / realized_volatility
        
        # Calculate position size
        base_risk = self.portfolio_value * self.max_risk_per_trade_pct
        position_size_usd = (base_risk / stop_loss_distance_pct) * vol_scalar
        
        # Cap at max risk
        position_size_usd = min(
            position_size_usd,
            self.portfolio_value * self.max_risk_per_trade_pct / stop_loss_distance_pct
        )
        
        position_size_base = position_size_usd / current_price
        risk_amount = position_size_usd * stop_loss_distance_pct
        
        return PositionSizeRecommendation(
            symbol=symbol,
            recommended_size_usd=position_size_usd,
            recommended_size_base=position_size_base,
            max_loss_usd=risk_amount,
            risk_percent=risk_amount / self.portfolio_value,
            sizing_method='VOLATILITY_BASED',
            confidence=0.85
        )
    
    def calculate_risk_parity_position(
        self,
        symbol: str,
        current_price: float,
        symbol_volatility: float,
        portfolio_volatilities: Dict[str, float],
        stop_loss_distance_pct: float
    ) -> PositionSizeRecommendation:
        """
        Risk parity: All positions contribute equal risk.
        """
        if not portfolio_volatilities or symbol_volatility <= 0:
            return self.calculate_volatility_position(
                symbol, current_price, symbol_volatility, stop_loss_distance_pct
            )
        
        # Calculate average portfolio volatility
        avg_vol = np.mean(list(portfolio_volatilities.values()))
        
        # This symbol's allocation (inverse to its volatility)
        vol_weight = avg_vol / symbol_volatility if symbol_volatility > 0 else 1.0
        
        # Normalize across portfolio
        total_weight = sum(avg_vol / v for v in portfolio_volatilities.values())
        allocation_pct = vol_weight / total_weight if total_weight > 0 else 0.1
        
        # Calculate position size
        position_size_usd = self.portfolio_value * allocation_pct
        position_size_base = position_size_usd / current_price
        risk_amount = position_size_usd * stop_loss_distance_pct
        
        return PositionSizeRecommendation(
            symbol=symbol,
            recommended_size_usd=position_size_usd,
            recommended_size_base=position_size_base,
            max_loss_usd=risk_amount,
            risk_percent=risk_amount / self.portfolio_value,
            sizing_method='RISK_PARITY',
            confidence=0.8
        )
    
    def calculate_fixed_fractional_position(
        self,
        symbol: str,
        current_price: float,
        allocation_pct: float,
        stop_loss_distance_pct: float
    ) -> PositionSizeRecommendation:
        """Simple fixed fraction of portfolio"""
        position_size_usd = self.portfolio_value * allocation_pct
        position_size_base = position_size_usd / current_price
        risk_amount = position_size_usd * stop_loss_distance_pct
        
        return PositionSizeRecommendation(
            symbol=symbol,
            recommended_size_usd=position_size_usd,
            recommended_size_base=position_size_base,
            max_loss_usd=risk_amount,
            risk_percent=risk_amount / self.portfolio_value,
            sizing_method='FIXED_FRACTIONAL',
            confidence=0.75
        )
    
    def _fallback_sizing(
        self,
        symbol: str,
        current_price: float,
        stop_loss_distance_pct: float
    ) -> PositionSizeRecommendation:
        """Fallback to simple 2% risk"""
        risk_amount = self.portfolio_value * self.max_risk_per_trade_pct
        position_size_usd = risk_amount / stop_loss_distance_pct
        position_size_base = position_size_usd / current_price
        
        return PositionSizeRecommendation(
            symbol=symbol,
            recommended_size_usd=position_size_usd,
            recommended_size_base=position_size_base,
            max_loss_usd=risk_amount,
            risk_percent=self.max_risk_per_trade_pct,
            sizing_method='FALLBACK_2PCT',
            confidence=0.6
        )
    
    def update_portfolio_value(self, new_value: float):
        """Update portfolio value (after P&L changes)"""
        self.portfolio_value = new_value
        logger.info(f"Portfolio value updated: ${new_value:,.2f}")



