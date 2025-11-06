"""
Circuit Breaker - Production Risk Management

Automatically halts trading when risk thresholds are breached.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal trading
    OPEN = "open"  # Trading halted
    HALF_OPEN = "half_open"  # Testing if conditions improved


@dataclass
class CircuitBreakerRule:
    """Circuit breaker rule definition"""
    name: str
    threshold: float
    check_function: callable
    cooldown_seconds: int = 300  # 5 minutes default


class CircuitBreaker:
    """
    Production circuit breaker for risk management.
    
    Rules:
    1. Daily loss limit: -5% of portfolio
    2. Rapid drawdown: -2% in 15 minutes
    3. Position count limit: max 10 open positions
    4. Consecutive losses: 5 in a row
    5. Volatility spike: >20% volatility increase
    """
    
    def __init__(
        self,
        max_daily_loss_pct: float = 0.05,
        max_rapid_drawdown_pct: float = 0.02,
        rapid_drawdown_window_minutes: int = 15,
        max_positions: int = 10,
        max_consecutive_losses: int = 5,
        max_volatility_spike_pct: float = 0.20,
        cooldown_seconds: int = 300
    ):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_rapid_drawdown_pct = max_rapid_drawdown_pct
        self.rapid_drawdown_window_minutes = rapid_drawdown_window_minutes
        self.max_positions = max_positions
        self.max_consecutive_losses = max_consecutive_losses
        self.max_volatility_spike_pct = max_volatility_spike_pct
        self.cooldown_seconds = cooldown_seconds
        
        # State
        self.state = CircuitBreakerState.CLOSED
        self.opened_at: Optional[datetime] = None
        self.opened_reason: Optional[str] = None
        
        # Tracking
        self.consecutive_losses = 0
        self.daily_pnl_history: List[Dict] = []
        self.recent_pnl_history: List[Dict] = []  # For rapid drawdown
        
        # Trip history
        self.trip_history: List[Dict] = []
        
        logger.info(
            f"CircuitBreaker initialized: "
            f"max_daily_loss={max_daily_loss_pct:.1%}, "
            f"max_rapid_drawdown={max_rapid_drawdown_pct:.1%}, "
            f"max_positions={max_positions}"
        )
    
    def check(
        self,
        portfolio_value: float,
        daily_pnl: float,
        open_positions: int,
        last_trade_pnl: Optional[float] = None,
        current_volatility: Optional[float] = None,
        baseline_volatility: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Check all circuit breaker conditions.
        
        Returns:
            Dict with 'allowed', 'reason', 'state'
        """
        now = datetime.now()
        
        # If circuit is open, check if cooldown elapsed
        if self.state == CircuitBreakerState.OPEN:
            if self.opened_at and (now - self.opened_at).total_seconds() > self.cooldown_seconds:
                logger.info("🔓 Circuit breaker cooldown elapsed, entering HALF_OPEN state")
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                remaining = self.cooldown_seconds - (now - self.opened_at).total_seconds()
                return {
                    'allowed': False,
                    'state': self.state.value,
                    'reason': f"Circuit breaker OPEN: {self.opened_reason}. Cooldown: {remaining:.0f}s",
                    'cooldown_remaining': remaining
                }
        
        # Check 1: Daily loss limit
        daily_loss_pct = (daily_pnl / portfolio_value) if portfolio_value > 0 else 0
        if abs(daily_loss_pct) >= self.max_daily_loss_pct and daily_pnl < 0:
            return self._trip_breaker(
                f"Daily loss limit breached: {daily_loss_pct:.2%} (limit: {self.max_daily_loss_pct:.2%})",
                "DAILY_LOSS_LIMIT"
            )
        
        # Check 2: Rapid drawdown
        self.recent_pnl_history.append({
            'timestamp': now,
            'pnl': daily_pnl,
            'portfolio_value': portfolio_value
        })
        
        # Keep only recent history
        cutoff = now - timedelta(minutes=self.rapid_drawdown_window_minutes)
        self.recent_pnl_history = [
            h for h in self.recent_pnl_history
            if h['timestamp'] > cutoff
        ]
        
        if len(self.recent_pnl_history) >= 2:
            first_value = self.recent_pnl_history[0]['portfolio_value']
            current_value = portfolio_value
            rapid_drawdown_pct = (current_value - first_value) / first_value if first_value > 0 else 0
            
            if abs(rapid_drawdown_pct) >= self.max_rapid_drawdown_pct and rapid_drawdown_pct < 0:
                return self._trip_breaker(
                    f"Rapid drawdown: {rapid_drawdown_pct:.2%} in {self.rapid_drawdown_window_minutes}min "
                    f"(limit: {self.max_rapid_drawdown_pct:.2%})",
                    "RAPID_DRAWDOWN"
                )
        
        # Check 3: Position count limit
        if open_positions >= self.max_positions:
            return self._trip_breaker(
                f"Position limit reached: {open_positions} (limit: {self.max_positions})",
                "POSITION_LIMIT"
            )
        
        # Check 4: Consecutive losses
        if last_trade_pnl is not None:
            if last_trade_pnl < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0
            
            if self.consecutive_losses >= self.max_consecutive_losses:
                return self._trip_breaker(
                    f"Consecutive losses: {self.consecutive_losses} (limit: {self.max_consecutive_losses})",
                    "CONSECUTIVE_LOSSES"
                )
        
        # Check 5: Volatility spike
        if current_volatility and baseline_volatility:
            volatility_increase = (current_volatility - baseline_volatility) / baseline_volatility
            if volatility_increase >= self.max_volatility_spike_pct:
                return self._trip_breaker(
                    f"Volatility spike: {volatility_increase:.2%} increase (limit: {self.max_volatility_spike_pct:.2%})",
                    "VOLATILITY_SPIKE"
                )
        
        # If in HALF_OPEN, one successful check closes the breaker
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info("✅ Circuit breaker checks passed in HALF_OPEN state, closing breaker")
            self.state = CircuitBreakerState.CLOSED
            self.opened_at = None
            self.opened_reason = None
        
        # All checks passed
        return {
            'allowed': True,
            'state': self.state.value,
            'reason': 'All checks passed',
            'consecutive_losses': self.consecutive_losses,
            'daily_loss_pct': daily_loss_pct
        }
    
    def _trip_breaker(self, reason: str, rule_name: str) -> Dict:
        """Trip the circuit breaker"""
        logger.error(f"🚨 CIRCUIT BREAKER TRIPPED: {reason}")
        
        self.state = CircuitBreakerState.OPEN
        self.opened_at = datetime.now()
        self.opened_reason = reason
        
        # Record trip
        self.trip_history.append({
            'timestamp': self.opened_at,
            'reason': reason,
            'rule': rule_name
        })
        
        return {
            'allowed': False,
            'state': self.state.value,
            'reason': reason,
            'rule': rule_name,
            'cooldown_seconds': self.cooldown_seconds
        }
    
    def manual_trip(self, reason: str = "Manual emergency stop"):
        """Manually trip the circuit breaker"""
        return self._trip_breaker(reason, "MANUAL")
    
    def manual_reset(self):
        """Manually reset the circuit breaker"""
        logger.warning("⚠️ Circuit breaker MANUALLY RESET")
        self.state = CircuitBreakerState.CLOSED
        self.opened_at = None
        self.opened_reason = None
        self.consecutive_losses = 0
    
    def get_status(self) -> Dict:
        """Get circuit breaker status"""
        return {
            'state': self.state.value,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'opened_reason': self.opened_reason,
            'consecutive_losses': self.consecutive_losses,
            'trip_count': len(self.trip_history),
            'last_trip': self.trip_history[-1] if self.trip_history else None,
            'cooldown_seconds': self.cooldown_seconds
        }
    
    def get_trip_history(self, limit: int = 10) -> List[Dict]:
        """Get recent trip history"""
        return self.trip_history[-limit:]

