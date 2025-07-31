"""
Enhanced Market Data Manager - Binance API Compatible
Comprehensive data schema matching Binance's format with unified Redis caching
"""

import asyncio
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import time
import os
import json
import redis
from contextlib import asynccontextmanager

# Broker configuration system
from config.broker_config import get_active_broker_config, get_broker_config_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketDepth:
    """Binance market depth entry"""
    price: float
    quantity: int
    orders: int

@dataclass
class DepthData:
    """Binance bid/ask depth"""
    buy: List[MarketDepth]
    sell: List[MarketDepth]

@dataclass
class OHLC:
    """Binance OHLC data"""
    open: float
    high: float
    low: float
    close: float

@dataclass
class BinanceQuote:
    """Complete Binance quote data - matches API response exactly"""
    symbol: str
    timestamp: str
    last_trade_time: Optional[str]
    last_price: float
    last_quantity: int
    buy_quantity: int
    sell_quantity: int
    volume: int
    average_price: float
    oi: float  # Open Interest
    oi_day_high: float
    oi_day_low: float
    net_change: float
    lower_circuit_limit: float
    upper_circuit_limit: float
    ohlc: OHLC
    depth: DepthData

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        return result

@dataclass
class Candle:
    """Binance historical candle data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    oi: Optional[float] = None  # For F&O instruments

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'oi': self.oi
        }

@dataclass
class EnhancedMarketData:
    """Enhanced market data container with all Binance fields"""
    # Core identification
    symbol: str
    instrument_token: int
    exchange: str
    
    # Price data
    last_price: float
    last_quantity: int
    last_trade_time: Optional[str]
    average_price: float
    net_change: float
    change_percent: float
    
    # OHLC data
    ohlc: OHLC
    
    # Volume and interest
    volume: int
    buy_quantity: int
    sell_quantity: int
    oi: float
    oi_day_high: float
    oi_day_low: float
    
    # Circuit limits
    lower_circuit_limit: float
    upper_circuit_limit: float
    
    # Market depth
    depth: DepthData
    
    # Historical data
    price_history: List[Candle]
    
    # Timestamps
    timestamp: str
    data_timestamp: datetime
    
    # Strategy-computed fields
    volatility: float = 0.0
    momentum: float = 0.0
    
    # Data quality
    data_quality: Dict[str, Any] = field(default_factory=dict)
    source: str = "binance"

    def __post_init__(self):
        if self.data_quality is None:
            self.data_quality = {
                'has_depth': len(self.depth.buy) > 0 or len(self.depth.sell) > 0,
                'has_oi': self.oi > 0,
                'price_valid': self.last_price > 0,
                'volume_valid': self.volume >= 0,
                'within_circuits': self.lower_circuit_limit <= self.last_price <= self.upper_circuit_limit
            }
        
        # Calculate change percentage if not provided
        if self.change_percent == 0 and self.ohlc.close > 0:
            self.change_percent = (self.net_change / self.ohlc.close) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert datetime to string
        result['data_timestamp'] = self.data_timestamp.isoformat()
        return result

    @classmethod
    def from_binance_ticker(cls, symbol: str, ticker_data: Dict[str, Any], price_history: List[Candle] = None) -> 'EnhancedMarketData':
        """Create EnhancedMarketData from Binance ticker API response"""
        
        # Extract OHLC from ticker data
        ohlc = OHLC(
            open=float(ticker_data.get('openPrice', 0.0)),
            high=float(ticker_data.get('highPrice', 0.0)),
            low=float(ticker_data.get('lowPrice', 0.0)),
            close=float(ticker_data.get('lastPrice', 0.0))
        )
        
        # Extract other data
        last_price = float(ticker_data.get('lastPrice', 0.0))
        net_change = float(ticker_data.get('priceChange', 0.0))
        change_percent = float(ticker_data.get('priceChangePercent', 0.0))
        volume = int(float(ticker_data.get('volume', 0.0)))
        
        # Create depth data
        buy_depth = []
        sell_depth = []
        
        # Extract exchange from symbol
        exchange = symbol.split(':')[0] if ':' in symbol else 'Binance'
        
        return cls(
            symbol=symbol,
            instrument_token=0,  # Not applicable for Binance
            exchange=exchange,
            last_price=last_price,
            last_quantity=int(ticker_data.get('lastQty', 0)),
            last_trade_time=None,  # Not provided by Binance
            average_price=float(ticker_data.get('weightedAvgPrice', 0.0)),
            net_change=net_change,
            change_percent=change_percent,
            ohlc=ohlc,
            volume=volume,
            buy_quantity=0,  # Not directly provided by Binance
            sell_quantity=0,  # Not directly provided by Binance
            oi=0.0,  # Not applicable for crypto
            oi_day_high=0.0,  # Not applicable for crypto
            oi_day_low=0.0,  # Not applicable for crypto
            lower_circuit_limit=0.0,  # Not applicable for crypto
            upper_circuit_limit=0.0,  # Not applicable for crypto
            depth=DepthData(buy=buy_depth, sell=sell_depth),
            price_history=price_history or [],
            timestamp=ticker_data.get('closeTime', datetime.now().isoformat()),
            data_timestamp=datetime.now()
        )

class BinanceMarketDataCache:
    """Unified Redis caching system for Binance market data"""
    
    def __init__(self, redis_url: str = None):
        self.redis_client = None
        self._setup_redis(redis_url)
        
        # Cache configuration
        self.quote_ttl = 60  # 1 minute for quotes
        self.historical_ttl = 3600  # 1 hour for historical data
        self.instruments_ttl = 86400  # 1 day for instruments list
        
    def _setup_redis(self, redis_url: str = None):
        """Setup Redis connection"""
        try:
            if not redis_url:
                redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            
            # Parse Redis URL
            from urllib.parse import urlparse
            import ssl
            
            parsed = urlparse(redis_url)
            redis_host = parsed.hostname or 'localhost'
            redis_port = parsed.port or 6379
            redis_password = parsed.password
            redis_db = int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0
            
            # Check if SSL is required
            ssl_required = 'ondigitalocean.com' in redis_host or redis_url.startswith('rediss://')
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                ssl=ssl_required,
                ssl_cert_reqs=ssl.CERT_NONE if ssl_required else None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"✅ Redis connected for Binance cache: {redis_host}:{redis_port}")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            self.redis_client = None
    
    def cache_quote(self, symbol: str, market_data: EnhancedMarketData):
        """Cache market data quote"""
        if not self.redis_client:
            return
        
        try:
            # Cache individual quote
            key = f"binance:quote:{symbol}"
            self.redis_client.setex(key, self.quote_ttl, json.dumps(market_data.to_dict()))
            
            # Cache in live data hash
            self.redis_client.hset("binance:live_quotes", symbol, json.dumps(market_data.to_dict()))
            self.redis_client.expire("binance:live_quotes", self.quote_ttl)
            
            # Update metadata
            self.redis_client.setex(f"binance:last_update:{symbol}", self.quote_ttl, datetime.now().isoformat())
            self.redis_client.setex("binance:symbols_count", self.quote_ttl, self.redis_client.hlen("binance:live_quotes"))
            
        except Exception as e:
            logger.error(f"❌ Redis cache error for {symbol}: {e}")
    
    def get_quote(self, symbol: str) -> Optional[EnhancedMarketData]:
        """Get cached market data quote"""
        if not self.redis_client:
            return None
        
        try:
            key = f"binance:quote:{symbol}"
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data_dict = json.loads(cached_data)
                # Reconstruct EnhancedMarketData object
                return self._dict_to_market_data(data_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Redis get error for {symbol}: {e}")
            return None
    
    def get_all_quotes(self) -> Dict[str, EnhancedMarketData]:
        """Get all cached quotes"""
        if not self.redis_client:
            return {}
        
        try:
            cached_data = self.redis_client.hgetall("binance:live_quotes")
            result = {}
            
            for symbol, data_json in cached_data.items():
                try:
                    data_dict = json.loads(data_json)
                    result[symbol] = self._dict_to_market_data(data_dict)
                except json.JSONDecodeError:
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Redis get all quotes error: {e}")
            return {}
    
    def cache_historical_data(self, symbol: str, interval: str, candles: List[Candle]):
        """Cache historical data"""
        if not self.redis_client:
            return
        
        try:
            key = f"binance:historical:{symbol}:{interval}"
            candles_data = [candle.to_dict() for candle in candles]
            self.redis_client.setex(key, self.historical_ttl, json.dumps(candles_data))
            
        except Exception as e:
            logger.error(f"❌ Redis historical cache error for {symbol}: {e}")
    
    def get_historical_data(self, symbol: str, interval: str) -> List[Candle]:
        """Get cached historical data"""
        if not self.redis_client:
            return []
        
        try:
            key = f"binance:historical:{symbol}:{interval}"
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                candles_data = json.loads(cached_data)
                candles = []
                for candle_dict in candles_data:
                    candles.append(Candle(
                        timestamp=datetime.fromisoformat(candle_dict['timestamp']),
                        open=candle_dict['open'],
                        high=candle_dict['high'],
                        low=candle_dict['low'],
                        close=candle_dict['close'],
                        volume=candle_dict['volume'],
                        oi=candle_dict.get('oi')
                    ))
                return candles
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Redis historical get error for {symbol}: {e}")
            return []
    
    def _dict_to_market_data(self, data_dict: Dict[str, Any]) -> EnhancedMarketData:
        """Convert dictionary back to EnhancedMarketData object"""
        
        # Reconstruct OHLC
        ohlc_data = data_dict.get('ohlc', {})
        ohlc = OHLC(
            open=ohlc_data.get('open', 0),
            high=ohlc_data.get('high', 0),
            low=ohlc_data.get('low', 0),
            close=ohlc_data.get('close', 0)
        )
        
        # Reconstruct depth
        depth_data = data_dict.get('depth', {'buy': [], 'sell': []})
        
        buy_depth = []
        for entry in depth_data.get('buy', []):
            buy_depth.append(MarketDepth(
                price=entry.get('price', 0),
                quantity=entry.get('quantity', 0),
                orders=entry.get('orders', 0)
            ))
        
        sell_depth = []
        for entry in depth_data.get('sell', []):
            sell_depth.append(MarketDepth(
                price=entry.get('price', 0),
                quantity=entry.get('quantity', 0),
                orders=entry.get('orders', 0)
            ))
        
        depth = DepthData(buy=buy_depth, sell=sell_depth)
        
        # Reconstruct price history
        price_history = []
        for candle_data in data_dict.get('price_history', []):
            price_history.append(Candle(
                timestamp=datetime.fromisoformat(candle_data['timestamp']),
                open=candle_data['open'],
                high=candle_data['high'],
                low=candle_data['low'],
                close=candle_data['close'],
                volume=candle_data['volume'],
                oi=candle_data.get('oi')
            ))
        
        return EnhancedMarketData(
            symbol=data_dict.get('symbol', ''),
            instrument_token=data_dict.get('instrument_token', 0),
            exchange=data_dict.get('exchange', 'Binance'),
            last_price=data_dict.get('last_price', 0),
            last_quantity=data_dict.get('last_quantity', 0),
            last_trade_time=data_dict.get('last_trade_time'),
            average_price=data_dict.get('average_price', 0),
            net_change=data_dict.get('net_change', 0),
            change_percent=data_dict.get('change_percent', 0),
            ohlc=ohlc,
            volume=data_dict.get('volume', 0),
            buy_quantity=data_dict.get('buy_quantity', 0),
            sell_quantity=data_dict.get('sell_quantity', 0),
            oi=data_dict.get('oi', 0),
            oi_day_high=data_dict.get('oi_day_high', 0),
            oi_day_low=data_dict.get('oi_day_low', 0),
            lower_circuit_limit=data_dict.get('lower_circuit_limit', 0),
            upper_circuit_limit=data_dict.get('upper_circuit_limit', 0),
            depth=depth,
            price_history=price_history,
            timestamp=data_dict.get('timestamp', ''),
            data_timestamp=datetime.fromisoformat(data_dict.get('data_timestamp', datetime.now().isoformat())),
            volatility=data_dict.get('volatility', 0.0),
            momentum=data_dict.get('momentum', 0.0),
            data_quality=data_dict.get('data_quality', {}),
            source=data_dict.get('source', 'binance')
        )

class EnhancedBinanceMarketDataManager:
    """Enhanced market data manager with complete Binance API compatibility"""
    
    def __init__(self, symbols: Optional[List[str]] = None, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # NO HARD-CODED SYMBOLS - ALL SYMBOLS MUST BE PROVIDED DYNAMICALLY
        if not symbols:
            raise ValueError("Symbols must be provided - no hard-coded symbols allowed")
        self.symbols = symbols
        
        # Initialize Binance client
        self.binance_client = None
        self.instruments_map = {}  # symbol -> instrument_token mapping
        
        # Initialize cache
        self.cache = BinanceMarketDataCache()
        
        # Configuration
        self.paper_trading_mode = (config or {}).get('paper_trading', True)
        self.update_interval = 1.0  # 1 second updates
        self.is_running = False
        
        logger.info(f"📊 Enhanced MarketDataManager initialized with {len(self.symbols)} symbols")
        logger.info(f"📝 Paper Trading: {'Enabled' if self.paper_trading_mode else 'Disabled'}")
        
        self._init_binance_client()
    
    def _init_binance_client(self):
        """Initialize Binance client"""
        try:
            # Get credentials from environment
            api_key = os.environ.get('BINANCE_API_KEY')
            api_secret = os.environ.get('BINANCE_API_SECRET')
            
            if not all([api_key, api_secret]):
                logger.error("❌ Binance credentials not found in environment variables")
                logger.error("Required: BINANCE_API_KEY, BINANCE_API_SECRET")
                return
            
            # Initialize Binance client
            from src.data.binance_client import BinanceClient
            self.binance_client = BinanceClient(api_key, api_secret)
            logger.info("✅ Binance client initialized for crypto trading")
            
            # Load instruments mapping
            asyncio.create_task(self._load_instruments_mapping())
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Binance client: {e}")
            self.binance_client = None
    
    async def _load_instruments_mapping(self):
        """Load instruments mapping for symbol to token conversion"""
        try:
            if not self.binance_client:
                return
            
            # For now, we'll use a placeholder for instruments mapping
            # This will be replaced with actual Binance instruments mapping
            logger.info("✅ Loaded Binance instruments mapping (placeholder)")
            
        except Exception as e:
            logger.error(f"❌ Failed to load instruments mapping: {e}")
    
    def get_instrument_token(self, symbol: str) -> Optional[int]:
        """Get instrument token for symbol"""
        # For now, we'll return a placeholder token
        # This will be replaced with actual Binance instrument token logic
        return 12345
    
    def _get_binance_symbol(self, symbol: str) -> str:
        """Convert symbol to Binance format"""
        # Binance symbols are typically in the format SYMBOLUSDT
        if symbol.endswith('USDT'):
            return symbol
        return f"{symbol}USDT"
    
    async def get_market_data(self, symbol: str) -> Optional[EnhancedMarketData]:
        """Get comprehensive market data for a symbol"""
        try:
            # Try cache first
            cached_data = self.cache.get_quote(symbol)
            if cached_data:
                return cached_data
            
            # Get from Binance API
            if not self.binance_client:
                logger.error("❌ Binance client not initialized")
                return None
            
            binance_symbol = self._get_binance_symbol(symbol)
            try:
                quote = self.binance_client.get_ticker(binance_symbol)
            except Exception as e:
                logger.error(f"❌ Error getting quote for {binance_symbol}: {e}")
                return None
            
            if not quote:
                logger.warning(f"⚠️ No quote data for {binance_symbol}")
                return None
            
            quote_data = quote
            
            # Get historical data
            instrument_token = self.get_instrument_token(symbol)
            price_history = []
            
            if instrument_token:
                try:
                    to_date = datetime.now()
                    from_date = to_date - timedelta(days=50)
                    
                    # Use Binance client for historical data
                    historical_data = self.binance_client.get_historical_klines(
                        symbol=symbol,
                        interval='1d',
                        start_str=str(int(from_date.timestamp() * 1000)),
                        end_str=str(int(to_date.timestamp() * 1000))
                    )
                    
                    # Process Binance kline data
                    for candle_data in historical_data:
                        price_history.append(Candle(
                            timestamp=datetime.fromtimestamp(candle_data[0] / 1000),
                            open=float(candle_data[1]),
                            high=float(candle_data[2]),
                            low=float(candle_data[3]),
                            close=float(candle_data[4]),
                            volume=float(candle_data[5]),
                            oi=0  # Binance doesn't provide OI data
                        ))
                
                except Exception as hist_error:
                    logger.warning(f"⚠️ Failed to get historical data for {symbol}: {hist_error}")
            
            # Create enhanced market data
            market_data = EnhancedMarketData(
                symbol=symbol,
                last_price=float(quote_data.get('lastPrice', 0.0)),
                volume=float(quote_data.get('volume', 0)),
                timestamp=quote_data.get('closeTime', datetime.now().isoformat())
            )
            
            # Cache the data
            self.cache.cache_quote(symbol, market_data)
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Error getting market data for {symbol}: {e}")
            return None
    
    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, EnhancedMarketData]:
        """Get market data for multiple symbols efficiently"""
        result = {}
        
        # Get symbols that aren't cached
        uncached_symbols = []
        for symbol in symbols:
            cached_data = self.cache.get_quote(symbol)
            if cached_data:
                result[symbol] = cached_data
            else:
                uncached_symbols.append(symbol)
        
        # Batch fetch uncached symbols
        if uncached_symbols and self.binance_client:
            try:
                binance_symbols = [self._get_binance_symbol(symbol) for symbol in uncached_symbols]
                # Get real-time ticker data from Binance
                quotes = {}
                for binance_symbol in binance_symbols:
                    try:
                        ticker_data = self.binance_client.get_ticker(binance_symbol)
                        quotes[binance_symbol] = ticker_data
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to get ticker for {binance_symbol}: {e}")
                        continue
                
                for symbol in uncached_symbols:
                    binance_symbol = self._get_binance_symbol(symbol)
                    if binance_symbol in quotes:
                        quote_data = quotes[binance_symbol]
                        market_data = EnhancedMarketData(
                            symbol=symbol,
                            last_price=float(quote_data.get('lastPrice', 0.0)),
                            volume=float(quote_data.get('volume', 0)),
                            timestamp=quote_data.get('closeTime', datetime.now().isoformat())
                        )
                        result[symbol] = market_data
                        
                        # Cache the data
                        self.cache.cache_quote(symbol, market_data)
                
            except Exception as e:
                logger.error(f"❌ Error getting multiple quotes: {e}")
        
        return result
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection and cache status"""
        return {
            'binance_connected': self.binance_client is not None,
            'paper_trading': self.paper_trading_mode,
            'redis_connected': self.cache.redis_client is not None,
            'instruments_loaded': len(self.instruments_map),
            'symbols_configured': len(self.symbols),
            'cache_stats': {
                'quotes_cached': self.cache.redis_client.hlen("binance:live_quotes") if self.cache.redis_client else 0
            }
        }

# Global instance for unified access
_enhanced_market_data_manager = None

def get_enhanced_market_data_manager() -> EnhancedBinanceMarketDataManager:
    """Get the global enhanced market data manager instance"""
    global _enhanced_market_data_manager
    if _enhanced_market_data_manager is None:
        from src.config.config_manager import ConfigManager
        config = ConfigManager.get_config()
        # Use a default symbol list for initialization
        default_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
        _enhanced_market_data_manager = EnhancedBinanceMarketDataManager(default_symbols, config)
    return _enhanced_market_data_manager 