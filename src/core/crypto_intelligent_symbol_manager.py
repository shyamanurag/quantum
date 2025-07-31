"""
Crypto Intelligent Symbol Management System
==========================================
Automatically manages crypto symbols for trading with intelligent strategy selection
Adapted from shares system for crypto markets (Binance)
- Auto-selects optimal crypto pairs based on market conditions
- Auto-adds new pairs based on volatility and opportunities  
- Auto-removes low-volume pairs
- Manages symbol limit intelligently
- Fully autonomous - no manual intervention required
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
import json
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class CryptoAutonomousConfig:
    """Configuration for autonomous crypto symbol management"""
    max_symbols: int = 100  # Crypto exchanges allow many symbols
    auto_refresh_interval: int = 3600  # 1 hour strategy re-evaluation
    pair_health_check_interval: int = 1800  # 30 minutes
    strategy_switch_interval: int = 900  # 15 minutes - check if strategy should change
    
    # Core crypto pairs (always subscribed - HIGHEST PRIORITY)
    core_pairs: List[str] = field(default_factory=lambda: [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOTUSDT',
        'LINKUSDT', 'LTCUSDT', 'BCHUSDT', 'XLMUSDT', 'EOSUSDT'
    ])
    
    # Autonomous decision parameters
    volatility_threshold_high: float = 5.0    # 5% hourly volatility = high 
    volatility_threshold_low: float = 1.0     # 1% hourly volatility = low
    volume_threshold: float = 1000000.0       # $1M daily volume minimum
    performance_lookback_hours: int = 24      # Look back 24 hours for performance

@dataclass
class CryptoPairMetrics:
    """Metrics for crypto pair evaluation"""
    symbol: str
    volume_24h: float = 0.0
    price_change_24h: float = 0.0
    volatility: float = 0.0
    market_cap_rank: int = 999
    trading_activity: float = 0.0
    last_updated: datetime = None

class CryptoIntelligentSymbolManager:
    """Fully autonomous crypto symbol management - no human intervention required"""
    
    def __init__(self, config: Optional[CryptoAutonomousConfig] = None):
        self.config = config or CryptoAutonomousConfig()
        self.active_symbols: Set[str] = set()
        self.current_strategy: str = "BALANCED"  # Will be auto-determined
        self.strategy_history: List[Dict] = []  # Track strategy changes
        self.symbol_metadata: Dict[str, Dict] = {}
        self.pair_metrics: Dict[str, CryptoPairMetrics] = {}
        self.is_running = False
        self.tasks = []
        
        # Performance tracking for autonomous decisions
        self.strategy_performance: Dict[str, Dict] = {
            "DeFi_FOCUS": {"trades": 0, "pnl": 0.0, "success_rate": 0.0},
            "BALANCED": {"trades": 0, "pnl": 0.0, "success_rate": 0.0},
            "MAJOR_PAIRS": {"trades": 0, "pnl": 0.0, "success_rate": 0.0},
            "ALTCOIN_FOCUS": {"trades": 0, "pnl": 0.0, "success_rate": 0.0}
        }
        
        logger.info("🤖 Crypto Intelligent Symbol Manager initialized")
        logger.info(f"   Max symbols: {self.config.max_symbols}")
        logger.info(f"   Strategy evaluation: Every {self.config.strategy_switch_interval/60:.1f} minutes")
        logger.info(f"   Fully autonomous: No manual intervention required")

    async def start(self):
        """Start the autonomous crypto symbol management"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("🚀 Starting Crypto Intelligent Symbol Manager...")
        
        # Initial autonomous symbol setup
        await self.autonomous_crypto_setup()
        
        # Start autonomous background tasks
        self.tasks = [
            asyncio.create_task(self.autonomous_strategy_monitor()),
            asyncio.create_task(self.autonomous_refresh_loop()),
            asyncio.create_task(self.pair_health_monitor_loop()),
            asyncio.create_task(self.performance_tracker_loop())
        ]
        
        logger.info("✅ Crypto Intelligent Symbol Manager started - operating independently")

    async def stop(self):
        """Stop the autonomous crypto symbol manager"""
        self.is_running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
            
        logger.info("🛑 Crypto Intelligent Symbol Manager stopped")

    async def autonomous_crypto_setup(self):
        """
        AUTONOMOUS SETUP: Automatically select and configure optimal crypto pairs
        No manual configuration required - fully intelligent selection
        """
        logger.info("🤖 Starting autonomous crypto symbol selection...")
        
        try:
            # Get intelligent crypto pair selection based on current market conditions
            optimal_pairs = await self._get_optimal_crypto_pairs()
            
            # Determine strategy based on market conditions
            self.current_strategy = await self._determine_optimal_strategy()
            
            logger.info(f"🧠 AUTONOMOUS DECISION: Selected {self.current_strategy} strategy")
            logger.info(f"📊 Crypto pair allocation: {len(optimal_pairs)} pairs")
            
            # Record strategy decision
            self.strategy_history.append({
                "timestamp": datetime.now().isoformat(),
                "strategy": self.current_strategy,
                "reason": "Initial autonomous crypto setup",
                "pair_count": len(optimal_pairs)
            })
            
            # Subscribe to selected pairs
            await self.autonomous_subscribe_pairs(optimal_pairs)
            
        except Exception as e:
            logger.error(f"❌ Autonomous crypto symbol selection failed: {e}")
            # Fallback to safe default
            optimal_pairs = self.config.core_pairs
            self.current_strategy = "BALANCED"
            logger.info("🔄 Using fallback crypto pairs for safety")
            await self.autonomous_subscribe_pairs(optimal_pairs)
        
        logger.info(f"✅ Autonomous crypto setup complete: {len(optimal_pairs)} pairs, strategy: {self.current_strategy}")

    async def _get_optimal_crypto_pairs(self) -> List[str]:
        """Get optimal crypto pairs based on current market conditions"""
        try:
            # Get market data for analysis (this would integrate with real Binance API)
            market_data = await self._fetch_crypto_market_data()
            
            # Analyze and score pairs
            scored_pairs = await self._score_crypto_pairs(market_data)
            
            # Select top pairs based on strategy
            optimal_pairs = await self._select_pairs_by_strategy(scored_pairs)
            
            return optimal_pairs
            
        except Exception as e:
            logger.error(f"❌ Error getting optimal crypto pairs: {e}")
            return self.config.core_pairs

    async def _fetch_crypto_market_data(self) -> Dict:
        """Fetch current crypto market data (placeholder for real Binance API)"""
        # This would integrate with real Binance API
        logger.info("📊 Fetching crypto market data...")
        
        # Placeholder market data structure
        return {
            "BTCUSDT": {"volume_24h": 15000000000, "price_change_24h": 2.5, "rank": 1},
            "ETHUSDT": {"volume_24h": 8000000000, "price_change_24h": 3.2, "rank": 2},
            "BNBUSDT": {"volume_24h": 2000000000, "price_change_24h": 1.8, "rank": 4},
            "ADAUSDT": {"volume_24h": 1500000000, "price_change_24h": 4.1, "rank": 6},
            "DOTUSDT": {"volume_24h": 800000000, "price_change_24h": 2.9, "rank": 8},
            "LINKUSDT": {"volume_24h": 600000000, "price_change_24h": 3.5, "rank": 12},
            "LTCUSDT": {"volume_24h": 1200000000, "price_change_24h": 1.2, "rank": 14},
            "UNIUSDT": {"volume_24h": 400000000, "price_change_24h": 5.2, "rank": 16},
            "AAVEUSDT": {"volume_24h": 300000000, "price_change_24h": 4.8, "rank": 18},
            "COMPUSDT": {"volume_24h": 200000000, "price_change_24h": 6.1, "rank": 20}
        }

    async def _score_crypto_pairs(self, market_data: Dict) -> List[Dict]:
        """Score crypto pairs based on multiple factors"""
        scored_pairs = []
        
        for symbol, data in market_data.items():
            # Calculate composite score
            volume_score = min(data["volume_24h"] / 1000000000, 10)  # Normalize to 10
            volatility_score = min(abs(data["price_change_24h"]), 5)  # Cap at 5
            rank_score = max(50 - data["rank"], 0) / 5  # Higher score for better rank
            
            total_score = volume_score + volatility_score + rank_score
            
            scored_pairs.append({
                "symbol": symbol,
                "score": total_score,
                "volume_24h": data["volume_24h"],
                "volatility": abs(data["price_change_24h"]),
                "rank": data["rank"]
            })
        
        # Sort by score descending
        scored_pairs.sort(key=lambda x: x["score"], reverse=True)
        return scored_pairs

    async def _determine_optimal_strategy(self) -> str:
        """Determine optimal trading strategy based on market conditions"""
        try:
            # This would analyze real market conditions
            # For now, use simple heuristics
            
            # Check overall market volatility (placeholder)
            market_volatility = 3.2  # This would come from real market analysis
            
            if market_volatility > 4.0:
                return "MAJOR_PAIRS"  # Focus on stable pairs during high volatility
            elif market_volatility < 2.0:
                return "ALTCOIN_FOCUS"  # Explore altcoins during low volatility
            else:
                return "BALANCED"  # Balanced approach
                
        except Exception as e:
            logger.error(f"❌ Error determining strategy: {e}")
            return "BALANCED"

    async def _select_pairs_by_strategy(self, scored_pairs: List[Dict]) -> List[str]:
        """Select pairs based on current strategy"""
        selected_pairs = set(self.config.core_pairs)  # Always include core pairs
        max_additional = self.config.max_symbols - len(selected_pairs)
        
        if self.current_strategy == "MAJOR_PAIRS":
            # Focus on top-ranked, high-volume pairs
            for pair in scored_pairs[:max_additional]:
                if pair["rank"] <= 10:  # Top 10 cryptocurrencies
                    selected_pairs.add(pair["symbol"])
                    
        elif self.current_strategy == "ALTCOIN_FOCUS":
            # Include promising altcoins
            for pair in scored_pairs[:max_additional]:
                if pair["rank"] > 10 and pair["volume_24h"] > self.config.volume_threshold:
                    selected_pairs.add(pair["symbol"])
                    
        else:  # BALANCED or DeFi_FOCUS
            # Balanced selection across all categories
            for pair in scored_pairs[:max_additional]:
                if pair["volume_24h"] > self.config.volume_threshold:
                    selected_pairs.add(pair["symbol"])
        
        return list(selected_pairs)

    async def autonomous_subscribe_pairs(self, pairs: List[str]):
        """Autonomously subscribe to crypto pairs"""
        try:
            new_pairs = [p for p in pairs if p not in self.active_symbols]
            
            if not new_pairs:
                return
                
            logger.info(f"🤖 Autonomously registering {len(new_pairs)} crypto pairs...")
            
            # Update tracking autonomously
            self.active_symbols.update(new_pairs)
            
            # Store metadata with autonomous classification
            timestamp = datetime.now().isoformat()
            for pair in new_pairs:
                self.symbol_metadata[pair] = {
                    'added_at': timestamp,
                    'type': self._classify_pair_autonomously(pair),
                    'priority': self._get_autonomous_priority(pair),
                    'strategy': self.current_strategy,
                    'auto_selected': True
                }
            
            logger.info(f"🤖 AUTONOMOUS: Registered {len(new_pairs)} crypto pairs")
            logger.info(f"📊 Total active: {len(self.active_symbols)} pairs")
            
        except Exception as e:
            logger.error(f"❌ Autonomous subscription error: {e}")

    async def autonomous_strategy_monitor(self):
        """AUTONOMOUS STRATEGY MONITORING: Continuously evaluate and switch strategies"""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.strategy_switch_interval)
                
                logger.info("🧠 Autonomous crypto strategy evaluation...")
                
                # Get current optimal strategy recommendation
                recommended_strategy = await self._determine_optimal_strategy()
                
                # Check if strategy should change
                if recommended_strategy != self.current_strategy:
                    await self._autonomous_strategy_switch(recommended_strategy)
                
                # Performance-based adjustment
                await self._performance_based_adjustment()
                
            except Exception as e:
                logger.error(f"❌ Autonomous strategy monitoring error: {e}")

    async def _autonomous_strategy_switch(self, new_strategy: str):
        """Autonomously switch to a new crypto trading strategy"""
        logger.info(f"🔄 AUTONOMOUS CRYPTO SWITCH: {self.current_strategy} → {new_strategy}")
        
        old_strategy = self.current_strategy
        self.current_strategy = new_strategy
        
        # Record the autonomous decision
        self.strategy_history.append({
            "timestamp": datetime.now().isoformat(),
            "strategy": new_strategy,
            "previous_strategy": old_strategy,
            "reason": "Autonomous crypto market condition change",
            "auto_decision": True
        })
        
        # Get new pair list for the strategy
        try:
            market_data = await self._fetch_crypto_market_data()
            scored_pairs = await self._score_crypto_pairs(market_data)
            new_pairs = await self._select_pairs_by_strategy(scored_pairs)
            
            # Update pairs autonomously
            await self.autonomous_subscribe_pairs(new_pairs)
            
            logger.info(f"✅ AUTONOMOUS: Successfully switched to {new_strategy} crypto strategy")
            
        except Exception as e:
            logger.error(f"❌ Autonomous crypto strategy switch failed: {e}")
            # Revert to previous strategy
            self.current_strategy = old_strategy

    async def _performance_based_adjustment(self):
        """Adjust crypto strategy based on autonomous performance analysis"""
        try:
            current_performance = self.strategy_performance.get(self.current_strategy, {})
            
            if current_performance.get("trades", 0) > 10:  # Minimum trades for evaluation
                success_rate = current_performance.get("success_rate", 0.0)
                
                if success_rate < 0.4:  # Less than 40% success rate
                    logger.info(f"🤖 AUTONOMOUS: Low crypto performance detected for {self.current_strategy}")
                    await self._consider_performance_switch()
                    
        except Exception as e:
            logger.error(f"❌ Crypto performance-based adjustment error: {e}")

    async def _consider_performance_switch(self):
        """Consider switching crypto strategy based on performance"""
        best_strategy = max(
            self.strategy_performance.keys(),
            key=lambda s: self.strategy_performance[s].get("success_rate", 0.0)
        )
        
        if best_strategy != self.current_strategy:
            best_performance = self.strategy_performance[best_strategy]
            if best_performance.get("success_rate", 0.0) > 0.6:  # 60% success rate
                logger.info(f"🤖 AUTONOMOUS: Switching to better performing crypto strategy: {best_strategy}")
                await self._autonomous_strategy_switch(best_strategy)

    async def autonomous_refresh_loop(self):
        """Autonomous refresh of crypto pairs and strategy"""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.auto_refresh_interval)
                
                logger.info("🔄 Autonomous crypto pair refresh...")
                
                # Refresh pairs based on current strategy
                await self.autonomous_crypto_setup()
                
                # Clean up any issues autonomously
                await self._autonomous_cleanup()
                
            except Exception as e:
                logger.error(f"❌ Autonomous crypto refresh error: {e}")

    async def pair_health_monitor_loop(self):
        """Monitor health of crypto pairs and remove low-performing ones"""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.pair_health_check_interval)
                
                logger.info("🔍 Crypto pair health check...")
                
                unhealthy_pairs = await self._find_unhealthy_pairs()
                if unhealthy_pairs:
                    await self._remove_unhealthy_pairs(unhealthy_pairs)
                
            except Exception as e:
                logger.error(f"❌ Crypto pair health monitor error: {e}")

    async def _find_unhealthy_pairs(self) -> List[str]:
        """Find crypto pairs with low volume or poor performance"""
        unhealthy = []
        
        try:
            market_data = await self._fetch_crypto_market_data()
            
            for symbol in self.active_symbols:
                if symbol in self.config.core_pairs:
                    continue  # Never remove core pairs
                    
                pair_data = market_data.get(symbol, {})
                volume_24h = pair_data.get("volume_24h", 0)
                
                # Remove pairs with low volume
                if volume_24h < self.config.volume_threshold:
                    unhealthy.append(symbol)
                    logger.info(f"⚠️ Low volume detected: {symbol} (${volume_24h:,.0f})")
                    
        except Exception as e:
            logger.error(f"❌ Error finding unhealthy crypto pairs: {e}")
        
        return unhealthy

    async def _remove_unhealthy_pairs(self, unhealthy_pairs: List[str]):
        """Remove unhealthy crypto pairs"""
        for symbol in unhealthy_pairs:
            self.active_symbols.discard(symbol)
            self.symbol_metadata.pop(symbol, None)
            
        logger.info(f"🧹 AUTONOMOUS: Removed {len(unhealthy_pairs)} unhealthy crypto pairs")

    async def performance_tracker_loop(self):
        """Track crypto performance for autonomous decision making"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Update performance metrics (placeholder - integrate with actual trading data)
                await self._update_crypto_performance_metrics()
                
            except Exception as e:
                logger.error(f"❌ Crypto performance tracking error: {e}")

    async def _update_crypto_performance_metrics(self):
        """Update crypto performance metrics for autonomous decisions"""
        # Placeholder for performance tracking
        # In production, this would integrate with actual crypto trading results
        pass

    async def _autonomous_cleanup(self):
        """Autonomous cleanup of poor-performing crypto pairs"""
        try:
            # Remove low-volume pairs
            unhealthy_pairs = await self._find_unhealthy_pairs()
            if unhealthy_pairs:
                await self._remove_unhealthy_pairs(unhealthy_pairs)
                
        except Exception as e:
            logger.error(f"❌ Autonomous crypto cleanup error: {e}")

    def _classify_pair_autonomously(self, pair: str) -> str:
        """Autonomously classify crypto pair type"""
        if pair in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']:
            return 'major'
        elif 'USDT' in pair:
            return 'altcoin'
        else:
            return 'exotic'

    def _get_autonomous_priority(self, pair: str) -> int:
        """Get autonomous priority for crypto pair"""
        if pair in self.config.core_pairs:
            return 1  # Highest priority
        elif pair in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']:
            return 2  # High priority
        elif any(defi in pair for defi in ['UNI', 'AAVE', 'COMP', 'SUSHI']):
            return 3  # Medium priority (DeFi tokens)
        else:
            return 4  # Lower priority

    def get_autonomous_status(self) -> Dict:
        """Get current autonomous crypto status"""
        return {
            'autonomous_mode': True,
            'market_type': 'crypto',
            'current_strategy': self.current_strategy,
            'active_pairs': len(self.active_symbols),
            'max_pairs': self.config.max_symbols,
            'utilization': f"{len(self.active_symbols)}/{self.config.max_symbols}",
            'strategy_switches_today': len([h for h in self.strategy_history 
                                          if h['timestamp'].startswith(datetime.now().strftime('%Y-%m-%d'))]),
            'last_strategy_change': self.strategy_history[-1] if self.strategy_history else None,
            'performance_tracking': True,
            'manual_intervention_required': False,
            'next_evaluation': datetime.now() + timedelta(seconds=self.config.strategy_switch_interval),
            'pair_health_status': 'monitoring' if self.is_running else 'stopped'
        }
    
    def get_status(self) -> Dict:
        """Get current status (alias for get_autonomous_status)"""
        return self.get_autonomous_status()

    def get_active_pairs(self) -> List[str]:
        """Get list of currently active crypto pairs"""
        return list(self.active_symbols)

# Global instance
_crypto_intelligent_manager = None

async def start_crypto_intelligent_management():
    """Start the crypto intelligent symbol management system"""
    global _crypto_intelligent_manager
    
    try:
        if _crypto_intelligent_manager is None:
            logger.info("🤖 Starting Crypto Intelligent Symbol Management System...")
            
            _crypto_intelligent_manager = CryptoIntelligentSymbolManager()
            await _crypto_intelligent_manager.start()
            
            logger.info("✅ Crypto Intelligent Symbol Management System started successfully")
            return True
        else:
            logger.info("⚠️ Crypto Intelligent Symbol Management already running")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to start Crypto Intelligent Symbol Management: {e}")
        return False

async def get_crypto_intelligent_manager() -> Optional[CryptoIntelligentSymbolManager]:
    """Get the global crypto intelligent manager instance"""
    return _crypto_intelligent_manager

async def get_crypto_intelligent_status():
    """Get current status of the crypto intelligent manager"""
    if _crypto_intelligent_manager:
        return _crypto_intelligent_manager.get_status()
    else:
        return {
            'status': 'not_running',
            'message': 'Crypto Intelligent Symbol Manager not initialized'
        }

async def stop_crypto_intelligent_management():
    """Stop the crypto intelligent symbol management system"""
    global _crypto_intelligent_manager
    
    try:
        if _crypto_intelligent_manager:
            await _crypto_intelligent_manager.stop()
            _crypto_intelligent_manager = None
            logger.info("🛑 Crypto Intelligent Symbol Management System stopped")
        return True
    except Exception as e:
        logger.error(f"❌ Error stopping Crypto Intelligent Symbol Management: {e}")
        return False