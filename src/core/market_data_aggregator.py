"""
Market Data Aggregator
Unifies data from Binance and broadcasts via WebSocket
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import redis.asyncio as redis

from .websocket_manager import WebSocketManager
from ..models.market_data_update import MarketDataUpdate

logger = logging.getLogger(__name__)

class MarketDataAggregator:
    """Aggregates market data from multiple sources"""
    
    def __init__(self, 
                 redis_client: redis.Redis,
                 websocket_manager: WebSocketManager):
        self.redis_client = redis_client
        self.websocket_manager = websocket_manager
        # No TrueData integration for crypto-only system
        # No Zerodha integration for crypto-only system
        self.is_running = False
        self.subscribed_symbols = set()
        
    async def initialize(self):
        """Initialize the aggregator"""
        try:
            # Use existing Binance cache instead of trying to connect
            # Binance is already connected and flowing data in the main app
            # For now, we'll use a placeholder for live market data
            # This will be replaced with actual Binance data feed
            live_market_data = {}
            is_connected = False
            
            if live_market_data and len(live_market_data) > 0:
                logger.info(f" Binance cache available: {len(live_market_data)} symbols")
                # Set up cache monitoring instead of direct connection
                # No TrueData integration for crypto-only system
            else:
                logger.warning(" Binance cache is empty - market data not available")
                # No TrueData integration for crypto-only system
            
            logger.info("Market data aggregator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize market data aggregator: {e}")
            raise
    
    async def start(self):
        """Start the aggregator"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start Binance listener
        # Binance listener for crypto-only system
        
        logger.info("Market data aggregator started")
    
    async def stop(self):
        """Stop the aggregator"""
        self.is_running = False
        # Binance disconnect for crypto-only system
        logger.info("Market data aggregator stopped")
    
    async def subscribe_symbol(self, symbol: str):
        """Subscribe to a symbol across all providers"""
        if symbol in self.subscribed_symbols:
            return
        
        self.subscribed_symbols.add(symbol)
        
        # Subscribe on Binance
        # Binance subscribe for crypto-only system
        
        # No Zerodha subscription for crypto-only system
        
        logger.info(f"Subscribed to {symbol} on all providers")
    
    async def unsubscribe_symbol(self, symbol: str):
        """Unsubscribe from a symbol"""
        if symbol not in self.subscribed_symbols:
            return
        
        self.subscribed_symbols.remove(symbol)
        
        # Unsubscribe from TrueData
        logger.info(f"Unsubscribed from {symbol} on all providers")
    
    async def _dummy_listener(self):
        """Dummy listener for crypto-only system"""
        while self.is_running:
            try:
                await asyncio.sleep(1)  # Small delay to prevent busy waiting
            except Exception as e:
                logger.error(f"Error in dummy listener: {e}")
                await asyncio.sleep(1)
    
    async def _handle_dummy_tick(self, tick_data: Dict):
        """Handle dummy tick data for crypto-only system"""
        try:
            pass
        except Exception as e:
            logger.error(f"Error handling dummy tick: {e}")
    
    async def _broadcast_market_data(self, market_update: MarketDataUpdate, provider: str):
        """Broadcast market data to WebSocket clients and store in database"""
        try:
            redis_key = f"market_data:{market_update.symbol}:latest"
            await self.redis_client.hset(redis_key, mapping={
                'price': market_update.price,
                'volume': market_update.volume,
                'timestamp': market_update.timestamp,
                'provider': provider
            })
            await self.redis_client.expire(redis_key, 3600)  # 1 hour expiry
            
            # Publish to Redis channel for WebSocket broadcast
            await self.redis_client.publish(
                'market_data',
                json.dumps({
                    **market_update.__dict__,
                    'provider': provider
                })
            )
            
            # Store tick data in database (implement database storage)
            # await self._store_tick_data(market_update, provider)
            
        except Exception as e:
            logger.error(f"Error broadcasting market data: {e}") 