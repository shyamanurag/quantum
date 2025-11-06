"""
Base Strategy Class
Provides common functionality for all trading strategies
"""
import logging
from datetime import datetime, time
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    Base strategy class with common functionality.
    All trading strategies should inherit from this class.
    """
    
    def __init__(self, name: str = "BaseStrategy"):
        self.name = name
        self.active = False
        logger.info(f"✅ {self.name} initialized")
    
    @abstractmethod
    async def generate_signals(self, market_data: Dict) -> list:
        """
        Generate trading signals based on market data.
        Must be implemented by child classes.
        """
        pass
    
    def check_trading_hours(self, signal: Any) -> bool:
        """
        Check if within trading hours.
        
        FIXED: option_type properly extracted from signal
        
        Args:
            signal: Trading signal with symbol, direction, etc.
            
        Returns:
            True if within trading hours, False otherwise
        """
        try:
            # FIX: Properly extract option_type from signal
            option_type = None
            
            # Try multiple attributes where option_type might be stored
            if hasattr(signal, 'option_type'):
                option_type = signal.option_type
            elif hasattr(signal, 'product_type'):
                product_type = signal.product_type
                # Check if product type indicates options
                if product_type in ['CE', 'PE', 'CALL', 'PUT', 'OPT']:
                    option_type = product_type
            elif hasattr(signal, 'instrument_type'):
                inst_type = signal.instrument_type
                if inst_type in ['CE', 'PE', 'CALL', 'PUT', 'OPTION', 'OPTIONS']:
                    option_type = inst_type
            
            # Check if symbol indicates options (e.g., NIFTY25NOV24500CE)
            if option_type is None and hasattr(signal, 'symbol'):
                symbol = signal.symbol.upper()
                if 'CE' in symbol or 'PE' in symbol or 'CALL' in symbol or 'PUT' in symbol:
                    option_type = 'CE' if 'CE' in symbol else 'PE'
            
            # Now safely check option_type (no longer undefined!)
            if option_type and option_type in ['CE', 'PE', 'CALL', 'PUT', 'OPT', 'OPTION']:
                # Options trading hours: 9:15 AM to 3:30 PM
                current_time = datetime.now().time()
                market_open = time(9, 15)
                market_close = time(15, 30)
                
                if not (market_open <= current_time <= market_close):
                    logger.warning(
                        f"⏸️ MARKET CLOSED - Skipping options signal for {signal.symbol}"
                    )
                    return False
                
                logger.debug(f"✅ Options trading hours OK for {signal.symbol}")
                return True
            
            # For equity/futures, different hours apply
            current_time = datetime.now().time()
            
            # Equity pre-market: 9:00 AM
            # Regular market: 9:15 AM to 3:30 PM
            # Post-market: 3:40 PM to 4:00 PM
            market_open = time(9, 0)
            market_close = time(16, 0)  # 4:00 PM
            
            if not (market_open <= current_time <= market_close):
                logger.warning(f"⏸️ MARKET CLOSED - Skipping signal for {signal.symbol}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking trading hours: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Default to allowing (fail-open for non-critical check)
            return True
    
    def is_option_signal(self, signal: Any) -> bool:
        """
        Check if signal is for options trading.
        
        Args:
            signal: Trading signal
            
        Returns:
            True if options signal, False otherwise
        """
        try:
            # Check various attributes
            if hasattr(signal, 'option_type') and signal.option_type:
                return True
            
            if hasattr(signal, 'product_type'):
                product = signal.product_type
                if product in ['CE', 'PE', 'CALL', 'PUT', 'OPT', 'OPTION']:
                    return True
            
            if hasattr(signal, 'instrument_type'):
                inst = signal.instrument_type
                if inst in ['CE', 'PE', 'OPTION', 'OPTIONS']:
                    return True
            
            # Check symbol pattern
            if hasattr(signal, 'symbol'):
                symbol = signal.symbol.upper()
                # Options symbols typically have CE/PE suffix or contain option indicators
                if any(indicator in symbol for indicator in ['CE', 'PE', 'CALL', 'PUT']):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if option signal: {e}")
            return False
    
    def get_option_details(self, signal: Any) -> Optional[Dict]:
        """
        Extract option details from signal.
        
        Args:
            signal: Trading signal
            
        Returns:
            Dict with option details or None if not an option
        """
        if not self.is_option_signal(signal):
            return None
        
        try:
            details = {
                'underlying': getattr(signal, 'underlying', None),
                'option_type': getattr(signal, 'option_type', None),
                'strike': getattr(signal, 'strike', None),
                'expiry': getattr(signal, 'expiry', None),
                'symbol': getattr(signal, 'symbol', None)
            }
            
            # Try to parse from symbol if details missing
            if not details['option_type'] and details['symbol']:
                symbol = details['symbol'].upper()
                if 'CE' in symbol:
                    details['option_type'] = 'CE'
                elif 'PE' in symbol:
                    details['option_type'] = 'PE'
            
            return details
            
        except Exception as e:
            logger.error(f"Error extracting option details: {e}")
            return None
    
    def activate(self):
        """Activate the strategy"""
        self.active = True
        logger.info(f"✅ {self.name} activated")
    
    def deactivate(self):
        """Deactivate the strategy"""
        self.active = False
        logger.info(f"⏸️ {self.name} deactivated")

