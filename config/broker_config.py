"""
Broker Configuration System
Allows easy switching between Zerodha (testing) and Sharekhan (production)
NO MOCK DATA - ALL DATA MUST BE REAL
"""

import os
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

class BrokerType(Enum):
    """Supported broker types"""
    BINANCE = "binance"

@dataclass
class BrokerConfig:
    """Broker configuration data - NO MOCK MODE"""
    name: str
    type: BrokerType
    paper_trading: bool
    # NO MOCK MODE - ALL DATA MUST BE REAL
    api_credentials: Dict[str, str]
    features: Dict[str, bool]
    description: str

class BrokerConfigManager:
    """Manages broker configurations and switching - NO MOCK DATA"""
    
    def __init__(self):
        self.configs = self._load_broker_configs()
        self.active_broker = self._get_active_broker()
    
    def _load_broker_configs(self) -> Dict[str, BrokerConfig]:
        """Load all broker configurations - NO MOCK CONFIGURATIONS"""
        return {
            'binance_testing': BrokerConfig(
                name="Binance Testing",
                type=BrokerType.BINANCE,
                paper_trading=True,
                api_credentials={
                    'api_key': os.getenv('BINANCE_API_KEY', ''),
                    'api_secret': os.getenv('BINANCE_API_SECRET', ''),
                },
                features={
                    'real_time_data': True,
                    'paper_trading': True,
                    'websocket_support': True,
                    'historical_data': True,
                    'order_management': True,
                    'portfolio_tracking': True,
                },
                description="Binance with paper trading for safe testing - REAL API REQUIRED"
            ),
            
            'binance_production': BrokerConfig(
                name="Binance Production",
                type=BrokerType.BINANCE,
                paper_trading=False,
                api_credentials={
                    'api_key': os.getenv('BINANCE_API_KEY', ''),
                    'api_secret': os.getenv('BINANCE_API_SECRET', ''),
                },
                features={
                    'real_time_data': True,
                    'paper_trading': False,
                    'websocket_support': True,
                    'historical_data': True,
                    'order_management': True,
                    'portfolio_tracking': True,
                },
                description="Binance with real live trading - REAL API REQUIRED"
            ),
        }
    
    def _get_active_broker(self) -> str:
        """Get the currently active broker from environment"""
        return os.getenv('ACTIVE_BROKER', 'binance_testing')
    
    def get_active_config(self) -> BrokerConfig:
        """Get the active broker configuration"""
        return self.configs.get(self.active_broker, self.configs['binance_testing'])
    
    def get_config(self, broker_name: str) -> Optional[BrokerConfig]:
        """Get a specific broker configuration"""
        return self.configs.get(broker_name)
    
    def list_brokers(self) -> Dict[str, str]:
        """List all available brokers with descriptions"""
        return {name: config.description for name, config in self.configs.items()}
    
    def switch_to_config(self, broker_name: str) -> bool:
        """Switch to a different broker"""
        if broker_name in self.configs:
            self.active_broker = broker_name
            # In a real implementation, you'd update environment variables
            # For now, we'll just update the instance
            return True
        return False
    
    def validate_broker_config(self, broker_name: str) -> Dict[str, Any]:
        """Validate a broker configuration - NO MOCK MODE"""
        if broker_name not in self.configs:
            return {
                'valid': False,
                'error': f'Unknown broker: {broker_name}',
                'missing_credentials': [],
                'available_features': {}
            }
        
        config = self.configs[broker_name]
        missing_credentials = []
        
        # Check required credentials - NO MOCK MODE BYPASS
        for key, value in config.api_credentials.items():
            if not value:
                missing_credentials.append(key)
        
        return {
            'valid': len(missing_credentials) == 0,
            'broker_name': config.name,
            'broker_type': config.type.value,
            'paper_trading': config.paper_trading,
            'missing_credentials': missing_credentials,
            'available_features': config.features,
            'description': config.description
        }
    
    def get_market_data_config(self) -> Dict[str, Any]:
        """Get market data configuration for the active broker"""
        config = self.get_active_config()
        
        return {
            'broker_type': config.type.value,
            'paper_trading': config.paper_trading,
            'credentials': config.api_credentials,
            'features': config.features
        }
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading configuration for the active broker"""
        config = self.get_active_config()
        
        return {
            'broker_type': config.type.value,
            'paper_trading': config.paper_trading,
            'credentials': config.api_credentials,
            'order_management': config.features.get('order_management', False),
            'portfolio_tracking': config.features.get('portfolio_tracking', False)
        }

# Global instance
_broker_config_manager = None

def get_broker_config_manager() -> BrokerConfigManager:
    """Get the global broker configuration manager"""
    global _broker_config_manager
    if _broker_config_manager is None:
        _broker_config_manager = BrokerConfigManager()
    return _broker_config_manager

def get_active_broker_config() -> BrokerConfig:
    """Get the active broker configuration - defaults to Binance testing for safety"""
    manager = get_broker_config_manager()
    return manager.get_active_config()

# Convenience functions
def is_paper_trading() -> bool:
    """Check if paper trading is enabled - defaults to True for safety"""
    config = get_active_broker_config()
    return config.paper_trading if config else True

def get_broker_type() -> str:
    """Get the active broker type - defaults to Binance for safety"""
    config = get_active_broker_config()
    return config.type.value if config else BrokerType.BINANCE.value

def switch_to_binance_testing():
    """Switch to Binance testing mode"""
    manager = get_broker_config_manager()
    manager.switch_to_config('binance_testing')

def switch_to_binance_production():
    """Switch to Binance production mode"""
    manager = get_broker_config_manager()
    manager.switch_to_config('binance_production')

# NO MOCK TESTING FUNCTION - ALL TESTING MUST USE REAL APIs 