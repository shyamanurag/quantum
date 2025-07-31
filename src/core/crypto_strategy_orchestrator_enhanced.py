# core/crypto_strategy_orchestrator_enhanced.py
"""
Enhanced Crypto Strategy Orchestrator - The Brain of the Smartest Algo
Integrates all 6 strategies with cutting-edge intelligence components
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
from collections import deque

# Initialize logger early to avoid NameError
logger = logging.getLogger(__name__)

# Import enhanced strategies
from ..strategies.crypto_momentum_surfer_enhanced import EnhancedCryptoMomentumSurfer
from ..strategies.crypto_confluence_amplifier_enhanced import EnhancedCryptoConfluenceAmplifier
from ..strategies.crypto_news_impact_scalper_enhanced import EnhancedCryptoNewsImpactScalper
from ..strategies.crypto_regime_adaptive_controller import CryptoRegimeAdaptiveController
from ..strategies.crypto_volatility_explosion_enhanced import EnhancedCryptoVolatilityExplosion
from ..strategies.crypto_volume_profile_scalper_enhanced import EnhancedCryptoVolumeProfileScalper

# Import enhanced components
from .crypto_risk_manager_enhanced import EnhancedCryptoRiskManager
from .crypto_trade_allocator_enhanced import EnhancedCryptoTradeAllocator
from .crypto_execution_engine import QuantumExecutionEngine

# Import edge intelligence with error handling
try:
    from ..edge.onchain_intelligence import OnChainIntelligence
    ONCHAIN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"OnChain intelligence not available: {e}")
    ONCHAIN_AVAILABLE = False

try:
    from ..edge.ai_predictor import QuantumAIPredictor
    AI_PREDICTOR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AI predictor not available: {e}")
    AI_PREDICTOR_AVAILABLE = False

try:
    from ..edge.social_analyzer import QuantumSocialAnalyzer
    SOCIAL_ANALYZER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Social analyzer not available: {e}")
    SOCIAL_ANALYZER_AVAILABLE = False

try:
    from ..edge.arbitrage_engine import CrossChainArbitrageEngine
    ARBITRAGE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Arbitrage engine not available: {e}")
    ARBITRAGE_AVAILABLE = False

try:
    from ..edge.risk_predictor import QuantumRiskPredictor
    RISK_PREDICTOR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Risk predictor not available: {e}")
    RISK_PREDICTOR_AVAILABLE = False

class EventBus:
    """Event bus for inter-component communication"""
    def __init__(self):
        self.subscribers = {}
    
    def subscribe(self, event_type: str, callback):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    async def publish(self, event_type: str, data: Dict):
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Event callback error: {e}")

class EnhancedCryptoStrategyOrchestrator:
    """
    The Smartest Crypto Trading System in the World
    Combines 6 sophisticated strategies with cutting-edge intelligence
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.event_bus = EventBus()
        
        # Initialize edge intelligence components with error handling
        logger.info("🧠 Initializing Edge Intelligence Components...")
        
        # OnChain Intelligence
        if ONCHAIN_AVAILABLE:
            try:
                self.onchain_intel = OnChainIntelligence(config.get('onchain_config', {}))
                logger.info("✅ OnChain Intelligence initialized")
            except Exception as e:
                logger.warning(f"⚠️ OnChain Intelligence failed: {e}")
                self.onchain_intel = None
        else:
            self.onchain_intel = None
            
        # AI Predictor
        if AI_PREDICTOR_AVAILABLE:
            try:
                self.ai_predictor = QuantumAIPredictor(config.get('ai_config', {}))
                logger.info("✅ AI Predictor initialized")
            except Exception as e:
                logger.warning(f"⚠️ AI Predictor failed: {e}")
                self.ai_predictor = None
        else:
            self.ai_predictor = None
            
        # Social Analyzer  
        if SOCIAL_ANALYZER_AVAILABLE:
            try:
                self.social_analyzer = QuantumSocialAnalyzer(config.get('social_config', {}))
                logger.info("✅ Social Analyzer initialized")
            except Exception as e:
                logger.warning(f"⚠️ Social Analyzer failed: {e}")
                self.social_analyzer = None
        else:
            self.social_analyzer = None
            
        # Arbitrage Engine
        if ARBITRAGE_AVAILABLE:
            try:
                self.arbitrage_engine = CrossChainArbitrageEngine(config.get('arbitrage_config', {}))
                logger.info("✅ Arbitrage Engine initialized")
            except Exception as e:
                logger.warning(f"⚠️ Arbitrage Engine failed: {e}")
                self.arbitrage_engine = None
        else:
            self.arbitrage_engine = None
            
        # Risk Predictor
        if RISK_PREDICTOR_AVAILABLE:
            try:
                self.risk_predictor = QuantumRiskPredictor(config.get('risk_prediction_config', {}))
                logger.info("✅ Risk Predictor initialized")
            except Exception as e:
                logger.warning(f"⚠️ Risk Predictor failed: {e}")
                self.risk_predictor = None
        else:
            self.risk_predictor = None
            
        # Core execution engine (always required)
        try:
            self.execution_engine = QuantumExecutionEngine(config.get('execution_config', {}))
            logger.info("✅ Execution Engine initialized")
        except Exception as e:
            logger.error(f"❌ Critical: Execution Engine failed: {e}")
            raise
        
        # Initialize enhanced risk management
        logger.info("🛡️ Initializing Enhanced Risk Management...")
        try:
            self.risk_manager = EnhancedCryptoRiskManager(
                config.get('crypto_risk', {}), 
                None,  # Position tracker will be injected
                self.event_bus
            )
            logger.info("✅ Risk Manager initialized")
        except Exception as e:
            logger.error(f"❌ Critical: Risk Manager failed: {e}")
            raise
        
        # Initialize enhanced trade allocation
        logger.info("📊 Initializing Enhanced Trade Allocation...")
        try:
            self.trade_allocator = EnhancedCryptoTradeAllocator(config.get('crypto_allocation', {}))
            logger.info("✅ Trade Allocator initialized")
        except Exception as e:
            logger.error(f"❌ Critical: Trade Allocator failed: {e}")
            raise
        
        # Enhanced strategy allocations with edge adjustments
        self.base_allocations = {
            'enhanced_momentum_surfer': 0.25,        # 25%
            'enhanced_confluence_amplifier': 0.20,    # 20%
            'enhanced_news_impact_scalper': 0.15,     # 15%
            'crypto_regime_adaptive_controller': 0.10, # 10%
            'enhanced_volatility_explosion': 0.15,    # 15%
            'enhanced_volume_profile_scalper': 0.15,  # 15%
        }
        
        # Initialize all strategies
        try:
            self._initialize_enhanced_strategies()
            logger.info("✅ Enhanced Strategies initialized")
        except Exception as e:
            logger.error(f"❌ Critical: Strategy initialization failed: {e}")
            raise
        
        # Performance tracking with edge metrics
        self.edge_performance = {
            'smart_money_accuracy': deque(maxlen=100),
            'liquidation_capture_rate': deque(maxlen=100),
            'ai_prediction_accuracy': deque(maxlen=100),
            'arbitrage_success_rate': deque(maxlen=100)
        }
        
        # System state - CRITICAL: Start as not initialized until initialize() succeeds
        self.is_running = False
        self.is_initialized = False  # Will be set to True only after successful initialize()
        self.emergency_mode = False
        self.last_learning_cycle = datetime.now()
        
        logger.info("🚀 Enhanced Crypto Strategy Orchestrator initialized successfully!")

    async def initialize(self):
        """Initialize the orchestrator and all components"""
        try:
            logger.info("🔧 Starting orchestrator initialization...")
            
            # Start risk manager
            if hasattr(self.risk_manager, 'start'):
                await self.risk_manager.start()
                
            # Start trade allocator
            if hasattr(self.trade_allocator, 'start'):
                await self.trade_allocator.start()
                
            # Start execution engine
            if hasattr(self.execution_engine, 'start'):
                await self.execution_engine.start()
                
            # Start edge intelligence components
            if self.onchain_intel and hasattr(self.onchain_intel, 'start'):
                await self.onchain_intel.start()
                
            if self.ai_predictor and hasattr(self.ai_predictor, 'start'):
                await self.ai_predictor.start()
                
            if self.social_analyzer and hasattr(self.social_analyzer, 'start'):
                await self.social_analyzer.start()
                
            if self.arbitrage_engine and hasattr(self.arbitrage_engine, 'start'):
                await self.arbitrage_engine.start()
                
            if self.risk_predictor and hasattr(self.risk_predictor, 'start'):
                await self.risk_predictor.start()
            
            # Start all strategies
            for strategy_name, strategy in self.strategies.items():
                if hasattr(strategy, 'start'):
                    await strategy.start()
                    logger.info(f"✅ Strategy {strategy_name} started")
            
            # CRITICAL: Set both flags for health check reporting
            self.is_initialized = True
            self.is_running = True
            
            logger.info("✅ Enhanced Crypto Strategy Orchestrator fully initialized and running!")
            
            # Return success for callers
            return True
            
        except Exception as e:
            logger.error(f"❌ Orchestrator initialization failed: {e}")
            # Set failure flags
            self.is_initialized = False
            self.is_running = False
            raise

    def _initialize_enhanced_strategies(self):
        """Initialize all enhanced strategies with edge intelligence"""
        self.strategies = {}
        
        # Enhanced traditional strategies
        self.strategies['enhanced_momentum_surfer'] = EnhancedCryptoMomentumSurfer({
            **self.config.get('momentum_config', {}),
            'onchain_intel': self.onchain_intel,
            'ai_predictor': self.ai_predictor,
            'social_analyzer': self.social_analyzer
        })
        
        self.strategies['enhanced_confluence_amplifier'] = EnhancedCryptoConfluenceAmplifier({
            **self.config.get('confluence_config', {}),
            'onchain_intel': self.onchain_intel
        })
        
        self.strategies['enhanced_news_impact_scalper'] = EnhancedCryptoNewsImpactScalper({
            **self.config.get('news_config', {}),
            'social_analyzer': self.social_analyzer
        })
        
        self.strategies['crypto_regime_adaptive_controller'] = CryptoRegimeAdaptiveController(
            self.config.get('regime_config', {})
        )
        
        self.strategies['enhanced_volatility_explosion'] = EnhancedCryptoVolatilityExplosion({
            **self.config.get('volatility_config', {}),
            'risk_predictor': self.risk_predictor
        })
        
        self.strategies['enhanced_volume_profile_scalper'] = EnhancedCryptoVolumeProfileScalper({
            **self.config.get('volume_config', {}),
            'onchain_intel': self.onchain_intel
        })
        
        logger.info(f"✅ Initialized {len(self.strategies)} enhanced strategies")

    async def start_quantum_trading(self):
        """Start the most advanced crypto trading operation"""
        try:
            if self.is_running:
                logger.warning("Quantum trading already running")
                return
            
            self.is_running = True
            
            # Start all components
            logger.info("⚡ Starting Quantum Trading System...")
            
            # Start edge intelligence services
            await asyncio.gather(
                self.onchain_intel.start(),
                self.ai_predictor.start(),
                self.social_analyzer.start(),
                self.arbitrage_engine.start(),
                self.risk_predictor.start()
            )
            
            # Start all strategies
            for name, strategy in self.strategies.items():
                await strategy.start()
                logger.info(f"✅ Started {name}")
            
            # Start main trading loop
            asyncio.create_task(self._quantum_trading_loop())
            
            # Start learning cycle
            asyncio.create_task(self._learning_cycle())
            
            logger.info("🌟 Quantum Trading System is now LIVE! 🌟")
            
        except Exception as e:
            logger.error(f"Failed to start quantum trading: {e}")
            await self.stop_quantum_trading()
            raise

    async def stop_quantum_trading(self):
        """Stop the quantum trading system"""
        logger.info("🛑 Stopping Quantum Trading System...")
        
        self.is_running = False
        
        try:
            # Stop all strategies
            for name, strategy in self.strategies.items():
                await strategy.stop()
                logger.info(f"⏹️ Stopped {name}")
            
            # Stop edge intelligence
            await asyncio.gather(
                self.onchain_intel.stop(),
                self.ai_predictor.stop(),
                self.social_analyzer.stop(),
                self.arbitrage_engine.stop(),
                self.risk_predictor.stop(),
                return_exceptions=True
            )
            
            logger.info("✅ Quantum Trading System stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping system: {e}")

    async def _quantum_trading_loop(self):
        """Main quantum trading loop with edge intelligence integration"""
        while self.is_running:
            try:
                # Gather intelligence from all edge sources
                intelligence = await self._gather_quantum_intelligence()
                
                # Generate signals from all strategies
                signals = await self._generate_enhanced_signals(intelligence)
                
                # Apply quantum signal fusion
                fused_signals = await self._quantum_signal_fusion(signals, intelligence)
                
                # Risk validation with predictive models
                validated_signals = await self._enhanced_risk_validation(fused_signals, intelligence)
                
                # Execute with zero slippage optimization
                if validated_signals:
                    await self._quantum_execution(validated_signals)
                
                # Update edge performance metrics
                await self._update_edge_metrics(intelligence)
                
                await asyncio.sleep(30)  # 30-second cycle for crypto
                
            except Exception as e:
                logger.error(f"Quantum trading loop error: {e}")
                await asyncio.sleep(60)

    async def _gather_quantum_intelligence(self) -> Dict:
        """Gather intelligence from all edge sources"""
        intelligence = {}
        
        try:
            # Gather from all sources in parallel
            results = await asyncio.gather(
                self.onchain_intel.get_smart_money_signals(),
                self.ai_predictor.get_market_predictions(),
                self.social_analyzer.get_viral_signals(),
                self.arbitrage_engine.get_arbitrage_opportunities(),
                self.risk_predictor.get_risk_predictions(),
                return_exceptions=True
            )
            
            intelligence.update({
                'smart_money': results[0] if not isinstance(results[0], Exception) else {},
                'ai_predictions': results[1] if not isinstance(results[1], Exception) else {},
                'social_signals': results[2] if not isinstance(results[2], Exception) else {},
                'arbitrage_ops': results[3] if not isinstance(results[3], Exception) else {},
                'risk_predictions': results[4] if not isinstance(results[4], Exception) else {}
            })
            
        except Exception as e:
            logger.error(f"Error gathering intelligence: {e}")
            
        return intelligence

    async def _generate_enhanced_signals(self, intelligence: Dict) -> List:
        """Generate signals from all strategies with edge intelligence"""
        all_signals = []
        
        for name, strategy in self.strategies.items():
            try:
                # Pass intelligence to strategy
                strategy_signals = await strategy.generate_signals_with_intelligence(intelligence)
                
                for signal in strategy_signals:
                    signal.strategy_name = name
                    signal.intelligence_score = self._calculate_intelligence_score(signal, intelligence)
                    all_signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error generating signals from {name}: {e}")
        
        return all_signals

    async def _quantum_signal_fusion(self, signals: List, intelligence: Dict) -> List:
        """Apply quantum signal fusion with edge intelligence weighting"""
        if not signals:
            return []
        
        # Group signals by symbol
        symbol_signals = {}
        for signal in signals:
            symbol = signal.symbol
            if symbol not in symbol_signals:
                symbol_signals[symbol] = []
            symbol_signals[symbol].append(signal)
        
        fused_signals = []
        
        for symbol, symbol_signal_list in symbol_signals.items():
            try:
                # Apply quantum fusion algorithm
                fused_signal = await self._apply_quantum_fusion(symbol_signal_list, intelligence)
                if fused_signal:
                    fused_signals.append(fused_signal)
                    
            except Exception as e:
                logger.error(f"Error fusing signals for {symbol}: {e}")
        
        return fused_signals

    async def _apply_quantum_fusion(self, signals: List, intelligence: Dict):
        """Apply the quantum signal fusion algorithm"""
        if len(signals) < 2:
            return signals[0] if signals else None
        
        # Calculate confluence score
        confluence_score = len(signals) / len(self.strategies)
        
        # Weight by intelligence
        intelligence_boost = 1.0
        
        # Smart money confirmation
        if intelligence.get('smart_money', {}).get('agreement', False):
            intelligence_boost *= 1.5
        
        # AI confidence boost
        ai_confidence = intelligence.get('ai_predictions', {}).get('confidence', 0)
        if ai_confidence > 0.8:
            intelligence_boost *= (1 + ai_confidence)
        
        # Social momentum boost
        social_score = intelligence.get('social_signals', {}).get('viral_score', 0)
        if social_score > 0.7:
            intelligence_boost *= (1 + social_score * 0.5)
        
        # Create fused signal
        base_signal = max(signals, key=lambda s: s.quality_score)
        base_signal.quality_score *= confluence_score * intelligence_boost
        base_signal.quantum_score = confluence_score * intelligence_boost
        
        return base_signal

    async def _enhanced_risk_validation(self, signals: List, intelligence: Dict) -> List:
        """Enhanced risk validation with predictive models"""
        validated_signals = []
        
        for signal in signals:
            try:
                # Traditional risk check
                risk_result = await self.risk_manager.validate_signal(signal)
                
                if not risk_result['approved']:
                    continue
                
                # Predictive risk check
                predictive_risk = intelligence.get('risk_predictions', {})
                
                # Black swan protection
                if predictive_risk.get('black_swan_probability', 0) > 0.6:
                    signal.position_size *= 0.5  # Reduce position size
                
                # Market manipulation detection
                if predictive_risk.get('manipulation_risk', 0) > 0.7:
                    continue  # Skip manipulated markets
                
                validated_signals.append(signal)
                
            except Exception as e:
                logger.error(f"Error validating signal: {e}")
        
        return validated_signals

    async def _quantum_execution(self, signals: List):
        """Execute signals with quantum optimization"""
        for signal in signals:
            try:
                # Allocate to users
                allocations = await self.trade_allocator.allocate_trade(signal)
                
                # Execute with quantum engine
                for allocation in allocations:
                    await self.execution_engine.execute_quantum_order(allocation)
                    
            except Exception as e:
                logger.error(f"Error executing signal: {e}")

    async def _update_edge_metrics(self, intelligence: Dict):
        """Update edge intelligence performance metrics"""
        try:
            # Update smart money accuracy
            smart_money_data = intelligence.get('smart_money', {})
            if 'accuracy' in smart_money_data:
                self.edge_performance['smart_money_accuracy'].append(smart_money_data['accuracy'])
            
            # Update AI prediction accuracy
            ai_data = intelligence.get('ai_predictions', {})
            if 'accuracy' in ai_data:
                self.edge_performance['ai_prediction_accuracy'].append(ai_data['accuracy'])
            
            # Update liquidation capture rate
            # ... more metrics
            
        except Exception as e:
            logger.error(f"Error updating edge metrics: {e}")

    async def _learning_cycle(self):
        """Continuous learning and optimization cycle"""
        while self.is_running:
            try:
                # Run learning cycle every hour
                await asyncio.sleep(3600)
                
                if datetime.now() - self.last_learning_cycle > timedelta(hours=1):
                    await self._run_learning_cycle()
                    self.last_learning_cycle = datetime.now()
                    
            except Exception as e:
                logger.error(f"Learning cycle error: {e}")

    async def _run_learning_cycle(self):
        """Run the learning and optimization cycle"""
        logger.info("🧠 Running Learning Cycle...")
        
        try:
            # Update AI models
            await self.ai_predictor.update_models()
            
            # Refresh smart wallet list
            await self.onchain_intel.refresh_smart_wallets()
            
            # Update social influence scores
            await self.social_analyzer.update_influence_scores()
            
            # Optimize strategy parameters
            await self._optimize_strategy_parameters()
            
            logger.info("✅ Learning cycle completed")
            
        except Exception as e:
            logger.error(f"Learning cycle error: {e}")

    async def _optimize_strategy_parameters(self):
        """Optimize strategy parameters based on performance"""
        # Implementation for parameter optimization
        pass

    def _calculate_intelligence_score(self, signal, intelligence: Dict) -> float:
        """Calculate intelligence score for a signal"""
        score = 1.0
        
        # Smart money factor
        if intelligence.get('smart_money', {}).get('agreement'):
            score *= 1.3
        
        # AI confidence factor
        ai_confidence = intelligence.get('ai_predictions', {}).get('confidence', 0)
        score *= (1 + ai_confidence * 0.5)
        
        # Social momentum factor
        social_score = intelligence.get('social_signals', {}).get('viral_score', 0)
        score *= (1 + social_score * 0.3)
        
        return score

    def get_quantum_metrics(self) -> Dict:
        """Get comprehensive quantum system metrics"""
        return {
            'system_state': {
                'active_strategies': len(self.strategies),
                'edge_services': 5,  # onchain, ai, social, arbitrage, risk
                'emergency_mode': self.emergency_mode
            },
            'edge_intelligence': {
                'smart_money_accuracy': np.mean(self.edge_performance['smart_money_accuracy']) if self.edge_performance['smart_money_accuracy'] else 0,
                'ai_prediction_accuracy': np.mean(self.edge_performance['ai_prediction_accuracy']) if self.edge_performance['ai_prediction_accuracy'] else 0,
                'liquidation_capture_rate': np.mean(self.edge_performance['liquidation_capture_rate']) if self.edge_performance['liquidation_capture_rate'] else 0,
                'arbitrage_success_rate': np.mean(self.edge_performance['arbitrage_success_rate']) if self.edge_performance['arbitrage_success_rate'] else 0
            },
            'traditional_performance': {
                strategy_name: strategy.get_performance_metrics() 
                for strategy_name, strategy in self.strategies.items()
            }
        } 