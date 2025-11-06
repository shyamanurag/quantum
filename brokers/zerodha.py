"""
Zerodha Broker Integration with Fixed Token Management
FIXES: Token sync, KiteConnect None errors, user identifier resolution
"""
import logging
import os
import redis
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from kiteconnect import KiteConnect

logger = logging.getLogger(__name__)


class ZerodhaClient:
    """
    Zerodha KiteConnect client with Redis-backed token management.
    
    FIXES:
    - Single source of truth for tokens (Redis)
    - Automatic reinitialization from Redis when client is None
    - Token validation after refresh
    - Proper user identifier mapping
    - Caching to prevent API hammering
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        redis_url: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv('ZERODHA_API_KEY')
        self.api_secret = api_secret or os.getenv('ZERODHA_API_SECRET')
        
        # Redis client for token storage
        redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("✅ Redis connected for Zerodha token storage")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis_client = None
        
        # State
        self.kite: Optional[KiteConnect] = None
        self.user_id: Optional[str] = None
        self.access_token: Optional[str] = None
        self.last_validated: Optional[datetime] = None
        
        # User identifier mapping (PAPER_TRADER_001 → QSW899)
        self.user_id_map = {
            'PAPER_TRADER_001': 'QSW899',
            'QSW899': 'QSW899',
            # Add more mappings as needed
        }
        
        # Cache for API calls (reduce hammering)
        self._margins_cache: Optional[Dict] = None
        self._margins_cache_expiry: Optional[datetime] = None
        self._positions_cache: Optional[Dict] = None
        self._positions_cache_expiry: Optional[datetime] = None
        self._orders_cache: Optional[list] = None
        self._orders_cache_expiry: Optional[datetime] = None
        
        # Try to initialize from Redis on startup
        self._try_init_from_redis()
        
        logger.info("🏗️ ZerodhaClient initialized")
    
    def _try_init_from_redis(self):
        """Try to initialize KiteConnect from Redis on startup"""
        if not self.redis_client:
            return
        
        try:
            # Try to find any stored token
            for user_id in ['QSW899', 'PAPER_TRADER_001']:
                redis_key = f"zerodha:token:{user_id}"
                token = self.redis_client.get(redis_key)
                
                if token:
                    logger.info(f"🔄 Found stored token for {user_id}, initializing...")
                    if self._reinit_kite(token, user_id):
                        logger.info(f"✅ Initialized from Redis for {user_id}")
                        return
        except Exception as e:
            logger.warning(f"⚠️ Could not init from Redis: {e}")
    
    def set_access_token(self, access_token: str, user_id: str) -> bool:
        """
        Set access token with Redis persistence and validation.
        
        This is the SINGLE SOURCE OF TRUTH for token updates.
        
        Args:
            access_token: Zerodha access token
            user_id: User ID (e.g., PAPER_TRADER_001 or QSW899)
            
        Returns:
            True if token set successfully
        """
        try:
            # Resolve user identifier
            actual_user_id = self.user_id_map.get(user_id, user_id)
            
            logger.info(f"🔄 Setting access token for user: {user_id} → {actual_user_id}")
            
            # Store in Redis (24 hour expiry)
            if self.redis_client:
                redis_key = f"zerodha:token:{actual_user_id}"
                self.redis_client.setex(redis_key, 86400, access_token)
                logger.info(f"✅ Token stored in Redis at {redis_key}")
            
            # Reinitialize KiteConnect instance
            success = self._reinit_kite(access_token, actual_user_id)
            
            if success:
                # Validate immediately
                if self._validate_token():
                    logger.info(f"✅ Token set and validated for {actual_user_id}")
                    return True
                else:
                    logger.error(f"❌ Token validation failed for {actual_user_id}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to set access token: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _reinit_kite(self, access_token: str, user_id: str) -> bool:
        """
        Reinitialize KiteConnect with new token.
        
        Args:
            access_token: Access token
            user_id: User ID
            
        Returns:
            True if successful
        """
        try:
            if not self.api_key:
                logger.error("❌ ZERODHA_API_KEY not set")
                return False
            
            logger.info(f"🔄 Reinitializing KiteConnect for {user_id}...")
            
            # Create new instance
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(access_token)
            
            # Store state
            self.user_id = user_id
            self.access_token = access_token
            
            # Clear caches
            self._clear_caches()
            
            logger.info(f"✅ KiteConnect reinitialized for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to reinitialize KiteConnect: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.kite = None
            self.access_token = None
            return False
    
    def _validate_token(self) -> bool:
        """
        Validate token by calling profile API.
        
        Returns:
            True if valid
        """
        try:
            if self.kite is None:
                logger.error("❌ Cannot validate: kite is None")
                return False
            
            profile = self.kite.profile()
            user_name = profile.get('user_name', 'Unknown')
            
            self.last_validated = datetime.utcnow()
            logger.info(f"✅ Token validated - User: {user_name}")
            return True
            
        except Exception as e:
            error_msg = str(e).lower()
            if "token" in error_msg or "unauthorized" in error_msg or "api_key" in error_msg:
                logger.error(f"❌ Token validation failed - Invalid credentials: {e}")
            else:
                logger.error(f"❌ Token validation failed: {e}")
            return False
    
    def _ensure_client(self) -> bool:
        """
        Ensure KiteConnect client is initialized.
        Attempts recovery from Redis if None.
        
        Returns:
            True if client available
        """
        if self.kite is not None:
            return True
        
        logger.warning("⚠️ Kite client is None - attempting to reinitialize")
        
        if not self.redis_client:
            logger.error("❌ Cannot recover: Redis not available")
            return False
        
        # Try to recover from Redis
        try:
            # Try current user_id first
            if self.user_id:
                redis_key = f"zerodha:token:{self.user_id}"
                token = self.redis_client.get(redis_key)
                
                if token:
                    logger.info(f"🔄 Recovered token from Redis for {self.user_id}")
                    if self._reinit_kite(token, self.user_id):
                        logger.info("✅ Client recovered successfully")
                        return True
            
            # Try common user IDs
            for user_id in ['QSW899', 'PAPER_TRADER_001']:
                redis_key = f"zerodha:token:{user_id}"
                token = self.redis_client.get(redis_key)
                
                if token:
                    logger.info(f"🔄 Found token for {user_id}, attempting recovery")
                    if self._reinit_kite(token, user_id):
                        logger.info(f"✅ Client recovered for {user_id}")
                        return True
            
            logger.error("❌ Cannot recover kite client from Redis - no valid tokens found")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error recovering client: {e}")
            return False
    
    def _clear_caches(self):
        """Clear all API caches"""
        self._margins_cache = None
        self._margins_cache_expiry = None
        self._positions_cache = None
        self._positions_cache_expiry = None
        self._orders_cache = None
        self._orders_cache_expiry = None
    
    def get_margins(self, segment: str = "equity") -> Optional[Dict]:
        """
        Get margins with caching and auto-recovery.
        
        Args:
            segment: Trading segment (equity, commodity)
            
        Returns:
            Margins dict or None
        """
        # Check cache
        if self._margins_cache and self._margins_cache_expiry:
            if datetime.utcnow() < self._margins_cache_expiry:
                logger.debug("📊 Using cached margins")
                return self._margins_cache
        
        # Ensure client available
        if not self._ensure_client():
            logger.error("❌ Kite client not available - cannot get margins")
            return None
        
        try:
            logger.debug(f"📊 Getting margins from Zerodha (segment: {segment})")
            
            margins = self.kite.margins(segment)
            
            # Cache for 10 seconds
            self._margins_cache = margins
            self._margins_cache_expiry = datetime.utcnow() + timedelta(seconds=10)
            
            available = margins.get('available', {}).get('live_balance', 0)
            logger.debug(f"✅ Got margins: ₹{available:,.0f}")
            return margins
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for auth errors
            if "token" in error_msg or "unauthorized" in error_msg or "403" in error_msg or "api_key" in error_msg:
                logger.error(f"❌ Token invalid or expired: {e}")
                self.kite = None  # Force reinit on next call
            else:
                logger.error(f"❌ Error getting margins: {e}")
            
            return None
    
    def get_positions(self) -> Optional[Dict]:
        """
        Get positions with caching and auto-recovery.
        
        Returns:
            Positions dict or None
        """
        # Check cache
        if self._positions_cache and self._positions_cache_expiry:
            if datetime.utcnow() < self._positions_cache_expiry:
                logger.debug("📊 Using cached positions")
                return self._positions_cache
        
        # Ensure client available
        if not self._ensure_client():
            logger.error("❌ Kite client not available - cannot get positions")
            return None
        
        try:
            logger.debug("📊 Getting positions from Zerodha")
            
            positions = self.kite.positions()
            
            # Cache for 5 seconds
            self._positions_cache = positions
            self._positions_cache_expiry = datetime.utcnow() + timedelta(seconds=5)
            
            net_count = len(positions.get('net', []))
            day_count = len(positions.get('day', []))
            
            logger.debug(f"✅ Got positions: {net_count} net, {day_count} day")
            return positions
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "token" in error_msg or "unauthorized" in error_msg:
                logger.error(f"❌ Token invalid: {e}")
                self.kite = None
            else:
                logger.error(f"❌ Error getting positions: {e}")
            
            return None
    
    def get_orders(self) -> Optional[list]:
        """
        Get orders with caching and auto-recovery.
        
        Returns:
            Orders list or None
        """
        # Check cache
        if self._orders_cache and self._orders_cache_expiry:
            if datetime.utcnow() < self._orders_cache_expiry:
                logger.debug("📊 Using cached orders")
                return self._orders_cache
        
        # Ensure client available
        if not self._ensure_client():
            logger.error("❌ Kite client not available - cannot get orders")
            return None
        
        try:
            logger.debug("📊 Getting orders from Zerodha")
            
            orders = self.kite.orders()
            
            # Cache for 10 seconds
            self._orders_cache = orders
            self._orders_cache_expiry = datetime.utcnow() + timedelta(seconds=10)
            
            logger.debug(f"✅ Got {len(orders)} orders")
            return orders
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "token" in error_msg or "unauthorized" in error_msg:
                logger.error(f"❌ Token invalid: {e}")
                self.kite = None
            else:
                logger.error(f"❌ Error getting orders: {e}")
            
            return None
    
    def place_order(self, **kwargs) -> Optional[str]:
        """
        Place order with auto-recovery.
        
        Returns:
            Order ID or None
        """
        # Ensure client available
        if not self._ensure_client():
            logger.error("❌ Kite client not available - cannot place order")
            return None
        
        try:
            symbol = kwargs.get('symbol', 'UNKNOWN')
            transaction_type = kwargs.get('transaction_type', 'UNKNOWN')
            logger.info(f"📤 Placing order: {symbol} {transaction_type}")
            
            order_id = self.kite.place_order(**kwargs)
            
            logger.info(f"✅ Order placed: {order_id}")
            
            # Clear caches
            self._orders_cache = None
            self._positions_cache = None
            
            return order_id
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "token" in error_msg or "unauthorized" in error_msg:
                logger.error(f"❌ Token invalid: {e}")
                self.kite = None
            else:
                logger.error(f"❌ Error placing order: {e}")
            
            return None
    
    def is_connected(self) -> bool:
        """Check if client is connected and valid"""
        if self.kite is None:
            return False
        
        # Revalidate if last check was > 5 minutes ago
        if self.last_validated is None or \
           (datetime.utcnow() - self.last_validated).total_seconds() > 300:
            return self._validate_token()
        
        return True
    
    def get_profile(self) -> Optional[Dict]:
        """Get user profile"""
        if not self._ensure_client():
            return None
        
        try:
            profile = self.kite.profile()
            return profile
        except Exception as e:
            logger.error(f"❌ Error getting profile: {e}")
            return None


# Singleton instance - SINGLE SOURCE OF TRUTH
_zerodha_client_instance: Optional[ZerodhaClient] = None


def get_zerodha_client() -> ZerodhaClient:
    """
    Get Zerodha client singleton.
    
    CRITICAL: This ensures ONLY ONE instance exists across entire application.
    All code must use this function instead of creating new instances.
    """
    global _zerodha_client_instance
    
    if _zerodha_client_instance is None:
        _zerodha_client_instance = ZerodhaClient()
        logger.info("✅ Created SINGLETON Zerodha client instance")
    
    return _zerodha_client_instance


# Legacy compatibility
zerodha_client = get_zerodha_client()

