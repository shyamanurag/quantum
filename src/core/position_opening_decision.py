"""
Position Opening Decision Logic
Evaluates whether to open new positions based on risk factors
"""
import logging
from enum import Enum
from datetime import datetime, date
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


# FIX: Define RiskLevel enum
class RiskLevel(Enum):
    """Risk levels for position evaluation"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PositionEvaluationResult:
    """Result of position opening evaluation"""
    
    def __init__(
        self,
        approved: bool,
        reason: str,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        checks: Dict[str, bool] = None
    ):
        self.approved = approved
        self.reason = reason
        self.risk_level = risk_level
        self.checks = checks or {}
        self.timestamp = datetime.utcnow()


class PositionOpeningDecision:
    """
    Evaluates whether to open a new position based on multiple risk factors.
    """
    
    def __init__(
        self,
        max_daily_loss_pct: float = 0.02,  # 2%
        max_positions: int = 10,
        min_confidence: float = 0.70
    ):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_positions = max_positions
        self.min_confidence = min_confidence
        
        # Daily tracking
        self.daily_pnl = 0.0
        self.starting_capital = 0.0
        self.last_reset_date: Optional[date] = None
        
        logger.info(f"✅ PositionOpeningDecision initialized")
    
    async def evaluate_position_opening(
        self,
        signal: Any,
        available_capital: float,
        current_positions: int,
        market_bias: Optional[str] = None,
        market_regime: Optional[str] = None
    ) -> PositionEvaluationResult:
        """
        Evaluate if position should be opened.
        """
        try:
            logger.info(f"🎯 EVALUATING POSITION OPENING: {signal.symbol} {signal.direction} @ ₹{signal.entry_price} (Confidence: {signal.confidence})")
            
            # Log context
            logger.info(f"📊 DATA FLOW CHECK #3 - Position Evaluation Context:")
            logger.info(f"   Available Capital: ₹{available_capital:,.0f}")
            logger.info(f"   Current Positions: {current_positions}")
            logger.info(f"   Market Bias Available: {market_bias is not None}")
            logger.info(f"   Market Bias: {market_bias}")
            logger.info(f"   Market Regime: {market_regime}")
            
            checks = {}
            
            # Check 1: Daily loss limit
            daily_loss_check = await self._check_daily_loss_limit(available_capital)
            checks["daily_loss"] = daily_loss_check.approved
            
            if not daily_loss_check.approved:
                return daily_loss_check
            
            # Check 2: Position limit
            if current_positions >= self.max_positions:
                return PositionEvaluationResult(
                    approved=False,
                    reason=f"Max positions reached ({current_positions}/{self.max_positions})",
                    risk_level=RiskLevel.HIGH,
                    checks=checks
                )
            checks["position_limit"] = True
            
            # Check 3: Minimum confidence
            if signal.confidence < self.min_confidence:
                return PositionEvaluationResult(
                    approved=False,
                    reason=f"Low confidence ({signal.confidence:.2f} < {self.min_confidence})",
                    risk_level=RiskLevel.MEDIUM,
                    checks=checks
                )
            checks["confidence"] = True
            
            # Check 4: Capital availability
            required_capital = getattr(signal, 'position_size_usd', 0) or getattr(signal, 'cost', 0)
            if required_capital > available_capital:
                return PositionEvaluationResult(
                    approved=False,
                    reason=f"Insufficient capital (need ₹{required_capital:,.0f}, have ₹{available_capital:,.0f})",
                    risk_level=RiskLevel.HIGH,
                    checks=checks
                )
            checks["capital"] = True
            
            # All checks passed
            logger.info(f"✅ POSITION APPROVED: {signal.symbol} - All checks passed")
            return PositionEvaluationResult(
                approved=True,
                reason="All risk checks passed",
                risk_level=RiskLevel.LOW,
                checks=checks
            )
            
        except Exception as e:
            logger.error(f"❌ Error evaluating position opening: {e}")
            logger.error(f"❌ Error type: {type(e)}")
            logger.error(f"❌ Error details: {str(e)}")
            
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            
            # Fail safe: reject on error
            return PositionEvaluationResult(
                approved=False,
                reason=f"Evaluation error: {str(e)}",
                risk_level=RiskLevel.CRITICAL
            )
    
    async def _check_daily_loss_limit(self, available_capital: float) -> PositionEvaluationResult:
        """
        Check if daily loss limit exceeded.
        """
        try:
            today = date.today()
            
            # Reset daily tracking on new day
            if self.last_reset_date != today:
                logger.info(f"📅 NEW TRADING DAY: Resetting daily loss tracking")
                logger.info(f"   Previous date: {self.last_reset_date}")
                logger.info(f"   Current date: {today}")
                logger.info(f"   Starting capital: ₹{available_capital:,.2f}")
                
                self.last_reset_date = today
                self.starting_capital = available_capital
                self.daily_pnl = 0.0
                
                max_loss = self.starting_capital * self.max_daily_loss_pct
                logger.info(f"   Daily loss limit: {self.max_daily_loss_pct:.1%} = ₹{max_loss:,.2f}")
            
            # Calculate daily P&L
            current_pnl = available_capital - self.starting_capital
            loss_pct = (current_pnl / self.starting_capital) if self.starting_capital > 0 else 0
            
            logger.info(f"✅ Daily P&L: {'+' if current_pnl >= 0 else ''}₹{current_pnl:,.2f} ({loss_pct:+.2%})")
            
            # Check if loss limit exceeded
            if current_pnl < 0 and abs(loss_pct) >= self.max_daily_loss_pct:
                return PositionEvaluationResult(
                    approved=False,
                    reason=f"Daily loss limit reached ({loss_pct:.2%} ≥ {self.max_daily_loss_pct:.2%})",
                    risk_level=RiskLevel.CRITICAL
                )
            
            # Warn if approaching limit
            if current_pnl < 0 and abs(loss_pct) >= self.max_daily_loss_pct * 0.8:
                logger.warning(f"⚠️ Approaching daily loss limit: {abs(loss_pct):.2%} of {self.max_daily_loss_pct:.2%}")
                risk_level = RiskLevel.HIGH
            elif current_pnl < 0 and abs(loss_pct) >= self.max_daily_loss_pct * 0.5:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            return PositionEvaluationResult(
                approved=True,
                reason=f"Daily P&L within limits ({loss_pct:+.2%})",
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error checking daily loss limit: {e}")
            
            # Fail safe: allow with medium risk
            return PositionEvaluationResult(
                approved=True,
                reason="Daily loss check failed, allowing with caution",
                risk_level=RiskLevel.MEDIUM
            )
    
    def update_daily_pnl(self, pnl: float):
        """Update daily P&L"""
        self.daily_pnl += pnl
        logger.info(f"📊 Daily P&L updated: ₹{self.daily_pnl:,.2f}")

