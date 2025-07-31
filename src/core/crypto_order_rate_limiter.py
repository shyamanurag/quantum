"""
Crypto Order Rate Limiter - Prevents Excessive Order Attempts
=============================================================
CRITICAL: Stops retry loops for crypto trading
Adapted from shares system to prevent API abuse on crypto exchanges
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict
from collections import defaultdict, deque
import hashlib

logger = logging.getLogger(__name__)

class CryptoOrderRateLimiter:
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.daily_order_count = 0
        self.minute_order_count = 0
        self.second_order_count = 0
        self.failed_orders = defaultdict(int)
        self.banned_symbols = set()
        self.processed_signals = set()
        
        # Conservative limits for crypto exchanges (Binance-based)
        self.limits = {
            'daily_max': 1500,          # Stay below exchange limits
            'minute_max': 120,          # Conservative for Binance
            'second_max': 5,            # Very conservative for crypto
            'max_failures_per_symbol': 3,  # Ban symbol after 3 failures
            'ban_duration': 600         # 10 minutes ban
        }
        
        # Time tracking
        self.last_minute_reset = time.time()
        self.last_second_reset = time.time()
        self.last_day_reset = datetime.now().date()
        
        logger.info("🛡️ CryptoOrderRateLimiter: Preventing crypto order loops")
    
    async def can_place_order(self, symbol: str, action: str, quantity: float, price: float = 0) -> Dict:
        # Reset counters if needed
        self._reset_counters_if_needed()
        
        # Check daily limit
        if self.daily_order_count >= self.limits['daily_max']:
            return {
                'allowed': False,
                'reason': 'DAILY_LIMIT_EXCEEDED',
                'message': f'Daily crypto order limit reached: {self.daily_order_count}/{self.limits["daily_max"]}'
            }
        
        # Check minute limit
        if self.minute_order_count >= self.limits['minute_max']:
            return {
                'allowed': False,
                'reason': 'MINUTE_LIMIT_EXCEEDED',
                'message': f'Minute crypto order limit reached: {self.minute_order_count}/{self.limits["minute_max"]}'
            }
        
        # Check second limit
        if self.second_order_count >= self.limits['second_max']:
            return {
                'allowed': False,
                'reason': 'SECOND_LIMIT_EXCEEDED',
                'message': f'Second crypto order limit reached: {self.second_order_count}/{self.limits["second_max"]}'
            }
        
        # Check if symbol is banned due to failures
        if symbol in self.banned_symbols:
            return {
                'allowed': False,
                'reason': 'SYMBOL_BANNED',
                'message': f'Crypto symbol {symbol} temporarily banned due to failures'
            }
        
        # Check for duplicate orders (use price for better uniqueness in crypto)
        order_signature = f"CRYPTO:{symbol}:{action}:{quantity}:{price:.4f}:{int(time.time() // 60)}"
        if order_signature in self.processed_signals:
            return {
                'allowed': False,
                'reason': 'DUPLICATE_ORDER',
                'message': f'Duplicate crypto order blocked: {symbol} {action}'
            }
        
        return {
            'allowed': True,
            'reason': 'APPROVED',
            'message': f'Crypto order approved: {self.daily_order_count+1}/{self.limits["daily_max"]}',
            'signature': order_signature
        }
    
    async def record_order_attempt(self, signature: str, success: bool, symbol: str = None, error: str = None):
        self.daily_order_count += 1
        self.minute_order_count += 1
        self.second_order_count += 1
        self.processed_signals.add(signature)
        
        if not success and symbol:
            self.failed_orders[symbol] += 1
            if self.failed_orders[symbol] >= self.limits['max_failures_per_symbol']:
                self.banned_symbols.add(symbol)
                logger.error(f"🚫 CRYPTO SYMBOL BANNED: {symbol} after {self.failed_orders[symbol]} failures")
                
                # Schedule unban after ban duration
                asyncio.create_task(self._unban_symbol_after_delay(symbol))
        
        logger.info(f"📊 Crypto Order recorded: {self.daily_order_count}/{self.limits['daily_max']}, Success: {success}")
    
    async def _unban_symbol_after_delay(self, symbol: str):
        """Unban symbol after ban duration"""
        await asyncio.sleep(self.limits['ban_duration'])
        if symbol in self.banned_symbols:
            self.banned_symbols.remove(symbol)
            logger.info(f"✅ CRYPTO SYMBOL UNBANNED: {symbol} after {self.limits['ban_duration']} seconds")
    
    def _reset_counters_if_needed(self):
        """Reset time-based counters"""
        current_time = time.time()
        current_date = datetime.now().date()
        
        # Reset daily counter
        if current_date > self.last_day_reset:
            self.daily_order_count = 0
            self.last_day_reset = current_date
            self.processed_signals.clear()
            logger.info("📅 Daily crypto order counters reset")
        
        # Reset minute counter
        if current_time - self.last_minute_reset >= 60:
            self.minute_order_count = 0
            self.last_minute_reset = current_time
        
        # Reset second counter
        if current_time - self.last_second_reset >= 1:
            self.second_order_count = 0
            self.last_second_reset = current_time
    
    def get_limits_status(self) -> Dict:
        """Get current limits status"""
        self._reset_counters_if_needed()
        
        return {
            'daily_orders': {
                'current': self.daily_order_count,
                'limit': self.limits['daily_max'],
                'remaining': self.limits['daily_max'] - self.daily_order_count
            },
            'minute_orders': {
                'current': self.minute_order_count,
                'limit': self.limits['minute_max'],
                'remaining': self.limits['minute_max'] - self.minute_order_count
            },
            'second_orders': {
                'current': self.second_order_count,
                'limit': self.limits['second_max'],
                'remaining': self.limits['second_max'] - self.second_order_count
            },
            'banned_symbols': list(self.banned_symbols),
            'failed_orders_by_symbol': dict(self.failed_orders)
        }

# Global instance for crypto
crypto_order_rate_limiter = CryptoOrderRateLimiter()