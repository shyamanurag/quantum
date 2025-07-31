"""
Signal Deduplication and Quality Filtering System - Crypto Adaptation
====================================================================
Prevents multiple signals for the same crypto symbol at the same timestamp
Implements signal quality scoring and filtering
Adapted from working shares trading system for crypto markets
"""

import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import os

logger = logging.getLogger(__name__)

class CryptoSignalDeduplicator:
    """Handles crypto signal deduplication and quality filtering"""
    
    def __init__(self):
        self.recent_signals = defaultdict(list)  # symbol -> list of recent signals
        self.signal_history = {}  # signal_id -> signal data
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = datetime.now()
        
        # Quality thresholds - BALANCED FOR CRYPTO TRADING
        self.min_confidence_threshold = 0.60  # Slightly lower for crypto volatility
        self.max_signals_per_symbol = 2  # Allow 2 signals per symbol per period 
        self.deduplication_window = 60  # 60 seconds window for crypto (faster than stocks)

        # 🚨 CRITICAL: Redis persistence for executed signals across deploys
        self.redis_client = None
        self._init_redis_connection()
        
        # 🚨 DEPLOYMENT CACHE CLEARING: Clear old signals after deployment
        asyncio.create_task(self._clear_signal_cache_on_startup())

    async def _clear_signal_cache_on_startup(self):
        """Clear deployment cache on startup to prevent duplicate crypto signals"""
        try:
            # Wait a bit for Redis connection to be ready
            await asyncio.sleep(2)
            
            if not self.redis_client:
                logger.warning("⚠️ No Redis client - cannot clear deployment cache")
                return
            
            # Check if this is a fresh deployment (no cache clearing in last 5 minutes)
            cache_clear_key = "crypto_last_cache_clear"
            last_clear = await self.redis_client.get(cache_clear_key)
            
            if last_clear:
                import time
                time_since_clear = time.time() - float(last_clear)
                if time_since_clear < 300:  # 5 minutes
                    logger.info(f"⏭️ Skipping crypto cache clear - last cleared {time_since_clear:.0f}s ago")
                    return
            
            logger.info("🧹 CRYPTO DEPLOYMENT STARTUP: Clearing signal execution cache")
            
            # Clear ONLY executed signals deduplication cache for today
            today = datetime.now().strftime('%Y-%m-%d')
            pattern = f"crypto_executed_signals:{today}:*"
            
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"✅ Cleared {deleted} crypto signal execution cache entries")
                logger.info("🔒 Crypto position tracking & order data preserved")
            else:
                logger.info("ℹ️ No crypto signal execution cache found - clean slate confirmed")
            
            # Mark cache as cleared
            import time
            await self.redis_client.set(cache_clear_key, str(time.time()), ex=3600)  # 1 hour expiry
            
            logger.info("🚀 Crypto signal processing cache cleared - ready for fresh signals")
            
        except Exception as e:
            logger.error(f"❌ Error clearing crypto deployment cache: {e}")

    def _init_redis_connection(self):
        """Initialize Redis connection for persistent crypto signal tracking"""
        try:
            import redis.asyncio as redis
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                self.redis_client = redis.from_url(
                    redis_url, 
                    decode_responses=True,
                    ssl_cert_reqs=None,
                    ssl_check_hostname=False
                )
                logger.info("✅ Crypto signal deduplicator Redis connection initialized")
                logger.info(f"🔗 Redis URL configured: {redis_url[:20]}...")
            else:
                logger.warning("⚠️ No REDIS_URL - crypto signal deduplication will be memory-only")
                logger.warning("🚨 CRITICAL: Without Redis, duplicate crypto signals across deployments CANNOT be prevented!")
        except Exception as e:
            logger.error(f"❌ Failed to init Redis for crypto signal deduplication: {e}")
            logger.error("🚨 CRITICAL: Redis connection failed - duplicate execution protection disabled!")
        
    async def _check_signal_already_executed(self, signal: Dict) -> bool:
        """Check if this crypto signal was already executed today (across deploys)"""
        try:
            if not self.redis_client:
                logger.warning(f"🚨 NO REDIS CLIENT: Cannot check for duplicate crypto signal {signal.get('symbol')} - allowing execution")
                return False
                
            symbol = signal.get('symbol')
            action = signal.get('action', 'BUY')
            
            # Check if signal was executed in last 24 hours
            today = datetime.now().strftime('%Y-%m-%d')
            executed_key = f"crypto_executed_signals:{today}:{symbol}:{action}"
            
            logger.info(f"🔍 CHECKING CRYPTO DUPLICATE: {executed_key}")
            executed_count = await self.redis_client.get(executed_key)
            
            if executed_count and int(executed_count) > 0:
                logger.warning(f"🚫 DUPLICATE CRYPTO SIGNAL BLOCKED: {symbol} {action} already executed {executed_count} times today")
                logger.warning(f"🔑 Redis key: {executed_key}")
                return True
            else:
                logger.info(f"✅ CRYPTO SIGNAL ALLOWED: {symbol} {action} - no previous executions found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error checking executed crypto signals in Redis: {e}")
            logger.error(f"🚨 REDIS CHECK FAILED for {signal.get('symbol')} - ALLOWING execution (risky)")
            return False
    
    async def mark_signal_executed(self, signal: Dict):
        """Mark crypto signal as executed to prevent future duplicates"""
        try:
            if not self.redis_client:
                logger.error(f"🚨 NO REDIS CLIENT: Cannot mark crypto signal {signal.get('symbol')} as executed - DUPLICATE RISK!")
                return
                
            symbol = signal.get('symbol')
            action = signal.get('action', 'BUY')
            
            # Increment execution count for today
            today = datetime.now().strftime('%Y-%m-%d')
            executed_key = f"crypto_executed_signals:{today}:{symbol}:{action}"
            
            logger.info(f"📝 MARKING CRYPTO AS EXECUTED: {executed_key}")
            current_count = await self.redis_client.incr(executed_key)
            await self.redis_client.expire(executed_key, 86400)  # 24 hours
            
            logger.info(f"✅ Marked crypto signal as executed: {symbol} {action} (count: {current_count})")
            
            if current_count > 1:
                logger.warning(f"⚠️ MULTIPLE CRYPTO EXECUTIONS DETECTED: {symbol} {action} now executed {current_count} times today!")
            
        except Exception as e:
            logger.error(f"❌ Error marking crypto signal as executed in Redis: {e}")
            logger.error(f"🚨 FAILED TO MARK {signal.get('symbol')} as executed - FUTURE DUPLICATES POSSIBLE!")
    
    async def process_signals(self, signals: List[Dict]) -> List[Dict]:
        """Process and deduplicate crypto signals, return only high-quality unique signals"""
        if not signals:
            return []
        
        # 🚨 CRITICAL: Check for already executed signals first
        filtered_signals = []
        for signal in signals:
            if await self._check_signal_already_executed(signal):
                continue  # Skip this signal - already executed
            filtered_signals.append(signal)
        
        if len(filtered_signals) < len(signals):
            logger.info(f"🚫 BLOCKED {len(signals) - len(filtered_signals)} duplicate crypto signals from previous executions")
        
        # Continue with normal processing
        signals = filtered_signals
        
        # Clean up old signals periodically
        self._cleanup_old_signals()
        
        # Filter by quality first
        quality_signals = self._filter_by_quality(signals)
        
        # Deduplicate by symbol
        deduplicated_signals = self._deduplicate_by_symbol(quality_signals)
        
        # Check for timestamp collisions and resolve
        final_signals = self._resolve_timestamp_collisions(deduplicated_signals)
        
        # Update signal history
        self._update_signal_history(final_signals)
        
        logger.info(f"📊 Crypto Signal Processing: {len(signals)} → {len(quality_signals)} → {len(final_signals)}")
        
        return final_signals
    
    def _filter_by_quality(self, signals: List[Dict]) -> List[Dict]:
        """Filter crypto signals by quality thresholds"""
        quality_signals = []
        rejection_stats = {
            'low_confidence': 0,
            'missing_fields': 0,
            'invalid_prices': 0,
            'poor_risk_reward': 0
        }
        
        for signal in signals:
            confidence = signal.get('confidence', 0)
            
            # Check minimum confidence
            if confidence < self.min_confidence_threshold:
                rejection_stats['low_confidence'] += 1
                logger.debug(f"❌ Crypto signal rejected - low confidence: {signal['symbol']} ({confidence:.2f} < {self.min_confidence_threshold})")
                continue
            
            # Check for required fields
            required_fields = ['symbol', 'action', 'entry_price', 'stop_loss', 'target']
            if not all(field in signal for field in required_fields):
                rejection_stats['missing_fields'] += 1
                logger.debug(f"❌ Crypto signal rejected - missing fields: {signal.get('symbol', 'UNKNOWN')}")
                continue
            
            # Check for reasonable price levels (crypto can have very different price ranges)
            entry_price = signal.get('entry_price', 0)
            stop_loss = signal.get('stop_loss', 0)
            target = signal.get('target', 0)
            
            if not all([entry_price > 0, stop_loss > 0, target > 0]):
                rejection_stats['invalid_prices'] += 1
                logger.debug(f"❌ Crypto signal rejected - invalid prices: {signal['symbol']}")
                continue
            
            # Check risk-reward ratio (crypto-adapted)
            if signal['action'] == 'BUY':
                risk = entry_price - stop_loss
                reward = target - entry_price
            else:  # SELL
                risk = stop_loss - entry_price
                reward = entry_price - target
            
            if risk <= 0 or reward <= 0:
                rejection_stats['invalid_prices'] += 1
                logger.debug(f"❌ Crypto signal rejected - invalid risk/reward: {signal['symbol']}")
                continue
            
            risk_reward_ratio = reward / risk
            if risk_reward_ratio < 1.2:  # Lower threshold for crypto due to volatility
                rejection_stats['poor_risk_reward'] += 1
                logger.debug(f"❌ Crypto signal rejected - poor risk/reward: {signal['symbol']} ({risk_reward_ratio:.2f} < 1.2)")
                continue
            
            quality_signals.append(signal)
        
        # Log summary of rejections
        if any(rejection_stats.values()):
            logger.info(f"📊 Crypto Quality Filter Results: {len(quality_signals)} passed, {sum(rejection_stats.values())} rejected")
            for reason, count in rejection_stats.items():
                if count > 0:
                    logger.info(f"   - {reason}: {count} signals")
        
        return quality_signals
    
    def _deduplicate_by_symbol(self, signals: List[Dict]) -> List[Dict]:
        """Remove duplicate signals for the same crypto symbol, keep highest confidence"""
        symbol_signals = defaultdict(list)
        
        # Group signals by symbol
        for signal in signals:
            symbol = signal['symbol']
            symbol_signals[symbol].append(signal)
        
        deduplicated = []
        
        for symbol, symbol_signal_list in symbol_signals.items():
            # Check if we already have recent signals for this symbol
            recent_count = len([s for s in self.recent_signals[symbol] 
                              if (datetime.now() - s['timestamp']).total_seconds() < self.deduplication_window])
            
            if recent_count >= self.max_signals_per_symbol:
                logger.debug(f"❌ Crypto signal rejected - too many recent signals: {symbol}")
                continue
            
            # If multiple signals for same symbol, keep the highest confidence
            if len(symbol_signal_list) > 1:
                best_signal = max(symbol_signal_list, key=lambda s: s.get('confidence', 0))
                logger.info(f"🔄 Crypto Deduplication: {symbol} - kept best of {len(symbol_signal_list)} signals")
                deduplicated.append(best_signal)
            else:
                deduplicated.append(symbol_signal_list[0])
        
        return deduplicated
    
    def _resolve_timestamp_collisions(self, signals: List[Dict]) -> List[Dict]:
        """Resolve timestamp collisions by adding microsecond precision and random suffix"""
        resolved_signals = []
        
        for i, signal in enumerate(signals):
            # Generate unique signal ID with microsecond precision
            timestamp = datetime.now()
            unique_id = f"CRYPTO_{signal['symbol']}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}_{i:03d}"
            
            # Add unique identifiers
            signal['signal_id'] = unique_id
            signal['generated_at'] = timestamp
            signal['deduplication_rank'] = i + 1
            signal['market_type'] = 'crypto'
            
            resolved_signals.append(signal)
        
        return resolved_signals
    
    def _update_signal_history(self, signals: List[Dict]):
        """Update signal history and recent signals tracking"""
        for signal in signals:
            symbol = signal['symbol']
            signal_id = signal['signal_id']
            
            # Add to signal history
            self.signal_history[signal_id] = signal
            
            # Add to recent signals for this symbol
            self.recent_signals[symbol].append({
                'signal_id': signal_id,
                'timestamp': signal['generated_at'],
                'confidence': signal['confidence']
            })
    
    def _cleanup_old_signals(self):
        """Clean up old crypto signals from memory"""
        if (datetime.now() - self.last_cleanup).total_seconds() < self.cleanup_interval:
            return
        
        cutoff_time = datetime.now() - timedelta(seconds=self.cleanup_interval)
        
        # Clean up recent signals
        for symbol in list(self.recent_signals.keys()):
            self.recent_signals[symbol] = [
                s for s in self.recent_signals[symbol] 
                if s['timestamp'] > cutoff_time
            ]
            
            # Remove empty entries
            if not self.recent_signals[symbol]:
                del self.recent_signals[symbol]
        
        # Clean up signal history
        old_signal_ids = [
            signal_id for signal_id, signal in self.signal_history.items()
            if signal['generated_at'] < cutoff_time
        ]
        
        for signal_id in old_signal_ids:
            del self.signal_history[signal_id]
        
        self.last_cleanup = datetime.now()
        logger.debug(f"🧹 Cleaned up {len(old_signal_ids)} old crypto signals")
    
    def get_signal_stats(self) -> Dict:
        """Get statistics about crypto signal processing"""
        total_recent = sum(len(signals) for signals in self.recent_signals.values())
        
        return {
            'total_recent_signals': total_recent,
            'symbols_with_signals': len(self.recent_signals),
            'signal_history_size': len(self.signal_history),
            'last_cleanup': self.last_cleanup.isoformat(),
            'min_confidence_threshold': self.min_confidence_threshold,
            'deduplication_window': self.deduplication_window,
            'market_type': 'crypto'
        }

# Global instance for crypto
crypto_signal_deduplicator = CryptoSignalDeduplicator()