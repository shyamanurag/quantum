"""
Volume Profile Analysis - Institutional Grade
Used for identifying high-volume price levels, support/resistance, and value areas
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class VolumeNode:
    """Represents a single price level with volume data"""
    price_level: float
    total_volume: float
    buy_volume: float
    sell_volume: float
    trade_count: int
    
    @property
    def imbalance(self) -> float:
        """Calculate buy/sell imbalance (-1 to +1)"""
        if self.total_volume == 0:
            return 0.0
        return (self.buy_volume - self.sell_volume) / self.total_volume
    
    @property
    def is_bullish(self) -> bool:
        """Check if this level shows bullish pressure"""
        return self.imbalance > 0.2
    
    @property
    def is_bearish(self) -> bool:
        """Check if this level shows bearish pressure"""
        return self.imbalance < -0.2


@dataclass
class POC:
    """Point of Control - Price level with highest volume"""
    price: float
    volume: float
    percentage_of_total: float


@dataclass
class ValueArea:
    """Value Area - Contains 70% of volume"""
    vah: float  # Value Area High
    val: float  # Value Area Low
    poc: POC
    volume_in_area: float
    total_volume: float
    
    @property
    def width(self) -> float:
        """Width of value area"""
        return self.vah - self.val
    
    @property
    def percentage(self) -> float:
        """Percentage of total volume in value area"""
        if self.total_volume == 0:
            return 0.0
        return (self.volume_in_area / self.total_volume) * 100


class VolumeProfile:
    """
    Institutional-grade volume profile analyzer
    
    Analyzes volume distribution across price levels to identify:
    - Point of Control (POC): highest volume price
    - Value Area: 70% of volume range
    - Support/Resistance from volume clusters
    - Volume imbalances (buying/selling pressure)
    """
    
    def __init__(self, tick_size: float = 0.001):
        """
        Initialize volume profile
        
        Args:
            tick_size: Price bucket size as percentage (0.001 = 0.1%)
        """
        self.tick_size = tick_size
        self.volume_nodes: Dict[float, VolumeNode] = {}
        self.total_volume = 0.0
        self.price_range = (float('inf'), float('-inf'))
        
    def add_trade(
        self,
        price: float,
        volume: float,
        side: str,  # 'BUY' or 'SELL'
        timestamp: Optional[float] = None
    ):
        """
        Add a trade to the volume profile
        
        Args:
            price: Trade price
            volume: Trade volume
            side: Trade side ('BUY' or 'SELL')
            timestamp: Trade timestamp (optional)
        """
        # Get price bucket
        price_bucket = self._get_price_bucket(price)
        
        # Initialize node if doesn't exist
        if price_bucket not in self.volume_nodes:
            self.volume_nodes[price_bucket] = VolumeNode(
                price_level=price_bucket,
                total_volume=0.0,
                buy_volume=0.0,
                sell_volume=0.0,
                trade_count=0
            )
        
        # Update node
        node = self.volume_nodes[price_bucket]
        node.total_volume += volume
        node.trade_count += 1
        
        if side == 'BUY':
            node.buy_volume += volume
        else:
            node.sell_volume += volume
        
        # Update totals
        self.total_volume += volume
        self.price_range = (
            min(self.price_range[0], price_bucket),
            max(self.price_range[1], price_bucket)
        )
    
    def _get_price_bucket(self, price: float) -> float:
        """Get price bucket for volume aggregation"""
        bucket_size = price * self.tick_size
        return round(price / bucket_size) * bucket_size
    
    def get_poc(self) -> Optional[POC]:
        """
        Get Point of Control (highest volume price level)
        
        Returns:
            POC object with price and volume data
        """
        if not self.volume_nodes:
            return None
        
        # Find node with highest volume
        max_node = max(self.volume_nodes.values(), key=lambda n: n.total_volume)
        
        return POC(
            price=max_node.price_level,
            volume=max_node.total_volume,
            percentage_of_total=(max_node.total_volume / self.total_volume * 100) if self.total_volume > 0 else 0
        )
    
    def get_value_area(self, percentage: float = 0.70) -> Optional[ValueArea]:
        """
        Calculate Value Area (contains specified percentage of volume)
        
        Args:
            percentage: Percentage of volume to include (default 0.70 = 70%)
            
        Returns:
            ValueArea object with VAH, VAL, and POC
        """
        if not self.volume_nodes or self.total_volume == 0:
            return None
        
        # Get POC
        poc = self.get_poc()
        if not poc:
            return None
        
        # Sort nodes by volume (descending)
        sorted_nodes = sorted(
            self.volume_nodes.values(),
            key=lambda n: n.total_volume,
            reverse=True
        )
        
        # Accumulate volume starting from POC
        target_volume = self.total_volume * percentage
        accumulated_volume = 0.0
        value_area_nodes = []
        
        for node in sorted_nodes:
            value_area_nodes.append(node)
            accumulated_volume += node.total_volume
            
            if accumulated_volume >= target_volume:
                break
        
        # Find VAH and VAL
        prices = [node.price_level for node in value_area_nodes]
        vah = max(prices)
        val = min(prices)
        
        return ValueArea(
            vah=vah,
            val=val,
            poc=poc,
            volume_in_area=accumulated_volume,
            total_volume=self.total_volume
        )
    
    def get_volume_at_price(self, price: float) -> float:
        """Get total volume at a specific price level"""
        price_bucket = self._get_price_bucket(price)
        node = self.volume_nodes.get(price_bucket)
        return node.total_volume if node else 0.0
    
    def get_imbalance_at_price(self, price: float) -> float:
        """Get buy/sell imbalance at a specific price level"""
        price_bucket = self._get_price_bucket(price)
        node = self.volume_nodes.get(price_bucket)
        return node.imbalance if node else 0.0
    
    def get_high_volume_nodes(self, percentile: float = 0.80) -> List[VolumeNode]:
        """
        Get price levels in top percentile by volume
        
        Args:
            percentile: Volume percentile threshold (0.80 = top 20%)
            
        Returns:
            List of high-volume nodes
        """
        if not self.volume_nodes:
            return []
        
        volumes = [node.total_volume for node in self.volume_nodes.values()]
        threshold = np.percentile(volumes, percentile * 100)
        
        return [
            node for node in self.volume_nodes.values()
            if node.total_volume >= threshold
        ]
    
    def get_support_resistance_levels(self, num_levels: int = 5) -> Tuple[List[float], List[float]]:
        """
        Identify support and resistance levels from volume profile
        
        Args:
            num_levels: Number of levels to return for each
            
        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        if not self.volume_nodes:
            return ([], [])
        
        # Get high volume nodes as potential SR levels
        high_vol_nodes = self.get_high_volume_nodes(percentile=0.75)
        
        # Sort by price
        high_vol_nodes.sort(key=lambda n: n.price_level)
        
        # Get current POC as reference
        poc = self.get_poc()
        if not poc:
            return ([], [])
        
        # Separate into support (below POC) and resistance (above POC)
        support = [n.price_level for n in high_vol_nodes if n.price_level < poc.price]
        resistance = [n.price_level for n in high_vol_nodes if n.price_level > poc.price]
        
        # Return top N levels
        support.reverse()  # Closest to current price first
        return (support[:num_levels], resistance[:num_levels])
    
    def get_volume_distribution(self) -> Dict[str, float]:
        """
        Get statistics about volume distribution
        
        Returns:
            Dictionary with distribution metrics
        """
        if not self.volume_nodes:
            return {}
        
        volumes = [node.total_volume for node in self.volume_nodes.values()]
        
        return {
            'total_volume': self.total_volume,
            'num_price_levels': len(self.volume_nodes),
            'avg_volume_per_level': np.mean(volumes),
            'std_volume': np.std(volumes),
            'max_volume': np.max(volumes),
            'min_volume': np.min(volumes),
            'volume_concentration': np.max(volumes) / self.total_volume if self.total_volume > 0 else 0
        }
    
    def clear(self):
        """Clear all volume profile data"""
        self.volume_nodes.clear()
        self.total_volume = 0.0
        self.price_range = (float('inf'), float('-inf'))

