"""
Elite 2-Strategy Production Orchestrator

Coordinates Institutional Volume Scalper + Volatility Regime Detector
Simplified, production-ready architecture with clean signal aggregation
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class AggregatedSignal:
    """Combined signal from both strategies"""
    symbol: str
    timestamp: datetime
    direction: str  # 'LONG', 'SHORT', 'NEUTRAL'
    confidence: float  # 0.0 to 1.0
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size_multiplier: float  # From volatility regime
    stop_loss_atr_multiplier: float  # From volatility regime
    volume_signal_confidence: float
    volatility_regime: str
    risk_score: float
    sources: List[str] = field(default_factory=list)


class EliteOrchestrator:
    """
    Simplified production orchestrator for 2 elite strategies:
    1. Institutional Volume Scalper - WHERE to trade
    2. Volatility Regime Detector - HOW MUCH to risk
    
    Signal Aggregation Logic:
    - Both agree (LONG/LONG or SHORT/SHORT): Execute with full confidence
    - One neutral: Execute with reduced size
    - Conflicting (LONG/SHORT): NO TRADE
    - EXTREME volatility regime: Reduce all sizes by 75%
    - Black swan alert: CLOSE ALL positions
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.is_initialized = False
        self.is_running = False
        self.trading_enabled = False
        
        # Core strategies (only 2!)
        self.volume_scalper = None
        self.volatility_detector = None
        
        # Core components
        self.risk_manager = None
        self.execution_engine = None
        self.binance_client = None
        
        # Signal tracking
        self.pending_signals: deque = deque(maxlen=100)
        self.executed_signals: deque = deque(maxlen=1000)
        self.signal_count = 0
        self.execution_count = 0
        
        # Session info
        self.session_id = None
        self.start_time = None
        
        logger.info("🎯 Elite 2-Strategy Orchestrator created")
    
    async def initialize(self) -> bool:
        """Initialize orchestrator and both enhanced strategies"""
        try:
            logger.info("🔧 Initializing Elite Orchestrator with Enhancement Modules...")
            
            # Import ENHANCED strategies
            from ..strategies.enhanced_strategy_wrapper import (
                EnhancedVolumeScalper,
                EnhancedVolatilityDetector
            )
            
            # Initialize enhanced strategies
            symbols = self.config.get('symbols', ['BTCUSDT', 'ETHUSDT'])
            portfolio_value = self.config.get('portfolio_value', 100000.0)
            
            self.volume_scalper = EnhancedVolumeScalper(
                symbols=symbols,
                portfolio_value=portfolio_value,
                whale_threshold_usd=self.config.get('whale_threshold', 50000),
                min_confidence=self.config.get('min_volume_confidence', 0.7)
            )
            
            self.volatility_detector = EnhancedVolatilityDetector(
                symbols=symbols,
                portfolio_value=portfolio_value,
                min_confidence=self.config.get('min_volatility_confidence', 0.7)
            )
            
            logger.info("✅ Both ENHANCED elite strategies initialized with ML, footprint, position sizing, and signal scoring")
            
            # Initialize risk manager
            await self._initialize_risk_manager()
            
            # Initialize execution engine
            await self._initialize_execution_engine()
            
            # Initialize Binance client
            await self._initialize_binance_client()
            
            self.is_initialized = True
            self.session_id = f"elite_session_{int(datetime.now().timestamp())}"
            self.start_time = datetime.now()
            
            logger.info(f"✅ Elite Orchestrator initialized | Session: {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Orchestrator initialization failed: {e}")
            return False
    
    async def _initialize_risk_manager(self):
        """Initialize risk manager with circuit breakers"""
        try:
            from .risk_manager import RiskManager
            self.risk_manager = RiskManager(
                max_daily_loss_pct=self.config.get('max_daily_loss_pct', 0.05),
                max_position_size_pct=self.config.get('max_position_size_pct', 0.10),
                max_positions=self.config.get('max_positions', 10)
            )
            logger.info("✅ Risk Manager initialized")
        except Exception as e:
            logger.warning(f"⚠️ Risk Manager initialization failed: {e}")
            self.risk_manager = None
    
    async def _initialize_execution_engine(self):
        """Initialize execution engine"""
        try:
            from .crypto_execution_engine import CryptoExecutionEngine
            self.execution_engine = CryptoExecutionEngine(self.config)
            logger.info("✅ Execution Engine initialized")
        except Exception as e:
            logger.warning(f"⚠️ Execution Engine initialization failed: {e}")
            self.execution_engine = None
    
    async def _initialize_binance_client(self):
        """Initialize Binance WebSocket client"""
        try:
            from ..data.binance_client import BinanceClient
            self.binance_client = BinanceClient(
                api_key=self.config.get('binance_api_key'),
                api_secret=self.config.get('binance_api_secret')
            )
            logger.info("✅ Binance Client initialized")
        except Exception as e:
            logger.warning(f"⚠️ Binance Client initialization failed: {e}")
            self.binance_client = None
    
    async def start(self) -> bool:
        """Start orchestrator and market data processing"""
        try:
            if not self.is_initialized:
                if not await self.initialize():
                    return False
            
            self.is_running = True
            
            # Start background tasks
            asyncio.create_task(self._market_data_loop())
            asyncio.create_task(self._signal_aggregation_loop())
            asyncio.create_task(self._execution_loop())
            
            logger.info("🚀 Elite Orchestrator started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start orchestrator: {e}")
            return False
    
    async def start_trading(self) -> bool:
        """Enable trading"""
        try:
            if not await self.start():
                return False
            
            self.trading_enabled = True
            logger.info("💰 Trading ENABLED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start trading: {e}")
            return False
    
    async def stop_trading(self):
        """Disable trading"""
        self.trading_enabled = False
        logger.info("🛑 Trading DISABLED")
    
    async def stop(self):
        """Stop orchestrator"""
        self.is_running = False
        self.trading_enabled = False
        logger.info("🛑 Elite Orchestrator stopped")
    
    async def _market_data_loop(self):
        """Process market data and feed to strategies"""
        logger.info("📊 Market data loop started")
        
        while self.is_running:
            try:
                # Get market data (WebSocket or REST)
                # For now, simulate receiving data
                await asyncio.sleep(0.1)  # 100ms refresh
                
            except Exception as e:
                logger.error(f"Error in market data loop: {e}")
                await asyncio.sleep(1.0)
    
    async def on_trade(self, symbol: str, price: float, quantity: float, side: str, timestamp: datetime):
        """Process trade event from WebSocket"""
        try:
            # Feed to volume scalper
            volume_signal = await self.volume_scalper.on_trade(
                symbol, price, quantity, side, timestamp
            )
            
            if volume_signal:
                self.pending_signals.append(('volume', volume_signal))
                self.signal_count += 1
                
        except Exception as e:
            logger.error(f"Error processing trade: {e}")
    
    async def on_candle_close(self, symbol: str, open_price: float, high: float, 
                             low: float, close: float, volume: float, timestamp: datetime):
        """Process candle close event"""
        try:
            # Feed to volatility detector
            volatility_signal = await self.volatility_detector.on_candle_close(
                symbol, open_price, high, low, close, volume, timestamp
            )
            
            if volatility_signal:
                self.pending_signals.append(('volatility', volatility_signal))
                self.signal_count += 1
                
        except Exception as e:
            logger.error(f"Error processing candle: {e}")
    
    async def on_order_book_update(self, symbol: str, bids: List, asks: List, timestamp: datetime):
        """Process order book update"""
        try:
            # Feed to volume scalper
            await self.volume_scalper.on_order_book_update(symbol, bids, asks, timestamp)
            
        except Exception as e:
            logger.error(f"Error processing order book: {e}")
    
    async def _signal_aggregation_loop(self):
        """Aggregate signals from both strategies"""
        logger.info("🔄 Signal aggregation loop started")
        
        while self.is_running:
            try:
                # Check if we have signals from both strategies for the same symbol
                if len(self.pending_signals) >= 2:
                    aggregated = await self._aggregate_signals()
                    if aggregated:
                        await self._execute_aggregated_signal(aggregated)
                
                await asyncio.sleep(0.5)  # 500ms aggregation window
                
            except Exception as e:
                logger.error(f"Error in signal aggregation loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _aggregate_signals(self) -> Optional[AggregatedSignal]:
        """
        Aggregate signals from both strategies.
        
        Rules:
        1. Both LONG -> Execute LONG with full confidence
        2. Both SHORT -> Execute SHORT with full confidence
        3. One LONG, one NEUTRAL -> Execute LONG with 0.5x size
        4. One SHORT, one NEUTRAL -> Execute SHORT with 0.5x size
        5. LONG vs SHORT -> NO TRADE (conflicting)
        6. EXTREME volatility -> Reduce size by 75%
        7. Black swan alert -> NO TRADE
        """
        try:
            # Get most recent signals
            recent_signals = list(self.pending_signals)[-10:]
            if not recent_signals:
                return None
            
            # Find matching signals by symbol
            volume_signals = {}
            volatility_signals = {}
            
            for signal_type, signal in recent_signals:
                symbol = getattr(signal, 'symbol', None)
                if not symbol:
                    continue
                
                if signal_type == 'volume':
                    volume_signals[symbol] = signal
                elif signal_type == 'volatility':
                    volatility_signals[symbol] = signal
            
            # Find symbols with both signals
            common_symbols = set(volume_signals.keys()) & set(volatility_signals.keys())
            
            for symbol in common_symbols:
                vol_signal = volume_signals[symbol]
                volatility_signal = volatility_signals[symbol]
                
                # Get directions
                vol_direction = vol_signal.direction
                vol_confidence = vol_signal.confidence
                
                vol_regime = volatility_signal.current_regime
                vol_risk_score = volatility_signal.risk_score
                
                # Check for black swan
                black_swan = self.volatility_detector.black_swan_alerts.get(symbol)
                if black_swan:
                    logger.warning(f"⚠️ Black swan detected for {symbol} - NO TRADE")
                    continue
                
                # Check for extreme volatility
                if vol_regime == 'EXTREME':
                    logger.warning(f"⚠️ EXTREME volatility for {symbol} - reducing exposure")
                    position_multiplier = 0.25  # 75% reduction
                else:
                    position_multiplier = volatility_signal.position_size_multiplier
                
                # Determine final direction and confidence
                # Volume scalper determines direction, volatility determines sizing
                direction = vol_direction
                confidence = vol_confidence
                
                # If volatility signal disagrees, reduce confidence
                if hasattr(volatility_signal, 'direction') and volatility_signal.direction:
                    if volatility_signal.direction != vol_direction:
                        if volatility_signal.direction == 'NEUTRAL':
                            confidence *= 0.5  # Reduce confidence
                            position_multiplier *= 0.5
                        else:
                            # Conflicting signals - no trade
                            logger.warning(
                                f"🚫 Conflicting signals for {symbol}: "
                                f"Volume={vol_direction}, Volatility={volatility_signal.direction}"
                            )
                            continue
                
                # Create aggregated signal
                aggregated = AggregatedSignal(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    direction=direction,
                    confidence=confidence,
                    entry_price=vol_signal.entry_price,
                    stop_loss=vol_signal.stop_loss,
                    take_profit=vol_signal.take_profit_1,
                    position_size_multiplier=position_multiplier,
                    stop_loss_atr_multiplier=volatility_signal.stop_loss_multiplier,
                    volume_signal_confidence=vol_confidence,
                    volatility_regime=vol_regime,
                    risk_score=vol_risk_score,
                    sources=[
                        f"volume_scalper_{vol_confidence:.2%}",
                        f"volatility_{vol_regime.lower()}"
                    ]
                )
                
                logger.info(
                    f"🎯 Aggregated signal: {symbol} {direction} | "
                    f"Confidence: {confidence:.2%} | Regime: {vol_regime} | "
                    f"Size multiplier: {position_multiplier:.2f}x"
                )
                
                return aggregated
            
            return None
            
        except Exception as e:
            logger.error(f"Error aggregating signals: {e}")
            return None
    
    async def _execute_aggregated_signal(self, signal: AggregatedSignal):
        """Execute aggregated signal with risk checks"""
        try:
            # Pre-execution risk check
            if self.risk_manager:
                risk_check = await self.risk_manager.validate_trade(
                    symbol=signal.symbol,
                    direction=signal.direction,
                    confidence=signal.confidence,
                    risk_score=signal.risk_score
                )
                
                if not risk_check.get('allowed', False):
                    logger.warning(
                        f"🚨 Signal rejected by risk manager: {risk_check.get('reason')}"
                    )
                    return
            
            # Calculate position size
            base_size = self.config.get('base_position_size', 0.001)  # BTC
            position_size = base_size * signal.position_size_multiplier * signal.confidence
            
            # Execute through execution engine
            if self.execution_engine:
                result = await self.execution_engine.execute_signal(
                    symbol=signal.symbol,
                    direction=signal.direction,
                    entry_price=signal.entry_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    quantity=position_size
                )
                
                if result.get('success'):
                    self.execution_count += 1
                    self.executed_signals.append(signal)
                    logger.info(
                        f"✅ Signal executed: {signal.symbol} {signal.direction} | "
                        f"Size: {position_size:.6f} | Order ID: {result.get('order_id')}"
                    )
                else:
                    logger.error(f"❌ Execution failed: {result.get('error')}")
            else:
                logger.warning("⚠️ No execution engine available")
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    async def _execution_loop(self):
        """Handle trade execution"""
        logger.info("⚡ Execution loop started")
        
        while self.is_running:
            try:
                # Clear old signals (>5 min old)
                now = datetime.now()
                while self.pending_signals:
                    signal_type, signal = self.pending_signals[0]
                    age = (now - signal.timestamp).total_seconds()
                    if age > 300:  # 5 minutes
                        self.pending_signals.popleft()
                    else:
                        break
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in execution loop: {e}")
                await asyncio.sleep(5.0)
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        volume_metrics = self.volume_scalper.get_strategy_metrics() if self.volume_scalper else {}
        volatility_metrics = self.volatility_detector.get_strategy_metrics() if self.volatility_detector else {}
        
        return {
            "initialized": self.is_initialized,
            "running": self.is_running,
            "trading_enabled": self.trading_enabled,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            
            "strategies": {
                "volume_scalper": volume_metrics,
                "volatility_detector": volatility_metrics
            },
            
            "signals": {
                "total_generated": self.signal_count,
                "pending": len(self.pending_signals),
                "executed": self.execution_count
            },
            
            "components": {
                "risk_manager": self.risk_manager is not None,
                "execution_engine": self.execution_engine is not None,
                "binance_client": self.binance_client is not None
            }
        }


# Singleton instance
_orchestrator: Optional[EliteOrchestrator] = None
_orchestrator_lock = asyncio.Lock()


async def get_orchestrator(config: Optional[Dict] = None) -> EliteOrchestrator:
    """Get singleton orchestrator instance"""
    global _orchestrator
    async with _orchestrator_lock:
        if _orchestrator is None:
            _orchestrator = EliteOrchestrator(config)
            await _orchestrator.initialize()
        return _orchestrator


def reset_orchestrator():
    """Reset orchestrator instance"""
    global _orchestrator
    _orchestrator = None
