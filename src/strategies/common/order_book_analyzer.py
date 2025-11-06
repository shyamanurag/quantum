"""
Order Book Analyzer - Institutional Grade
Real-time order book analysis for market microstructure insights
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


@dataclass
class OrderBookLevel:
    """Single order book level (bid or ask)"""
    price: float
    quantity: float
    
    @property
    def value(self) -> float:
        """Total value at this level"""
        return self.price * self.quantity


@dataclass
class OrderBookImbalance:
    """Order book imbalance metrics"""
    bid_volume: float
    ask_volume: float
    imbalance_ratio: float  # (bid - ask) / (bid + ask), range -1 to +1
    spread: float
    mid_price: float
    liquidity_score: float  # 0 to 1, higher = more liquid
    pressure: str  # "BUY", "SELL", or "NEUTRAL"
    
    @property
    def is_bullish(self) -> bool:
        """Check if order book shows bullish pressure"""
        return self.imbalance_ratio > 0.2
    
    @property
    def is_bearish(self) -> bool:
        """Check if order book shows bearish pressure"""
        return self.imbalance_ratio < -0.2


class OrderBookAnalyzer:
    """
    Institutional-grade order book analyzer
    
    Analyzes Level 2 market data to detect:
    - Bid/ask imbalances
    - Support/resistance levels from liquidity
    - Iceberg orders (hidden liquidity)
    - Spread anomalies
    - Market depth and liquidity
    """
    
    def __init__(self, depth_levels: int = 50):
        """
        Initialize order book analyzer
        
        Args:
            depth_levels: Number of price levels to analyze on each side
        """
        self.depth_levels = depth_levels
        self.bids: List[OrderBookLevel] = []
        self.asks: List[OrderBookLevel] = []
        self.last_update_time = 0
        
        # Historical tracking
        self.spread_history = deque(maxlen=1000)
        self.imbalance_history = deque(maxlen=1000)
        
    def update(self, bids: List[Tuple[float, float]], asks: List[Tuple[float, float]]):
        """
        Update order book with new data
        
        Args:
            bids: List of (price, quantity) tuples for bids
            asks: List of (price, quantity) tuples for asks
        """
        # Convert to OrderBookLevel objects
        self.bids = [
            OrderBookLevel(price=price, quantity=qty)
            for price, qty in bids[:self.depth_levels]
        ]
        
        self.asks = [
            OrderBookLevel(price=price, quantity=qty)
            for price, qty in asks[:self.depth_levels]
        ]
        
        # Sort bids descending (highest first)
        self.bids.sort(key=lambda x: x.price, reverse=True)
        
        # Sort asks ascending (lowest first)
        self.asks.sort(key=lambda x: x.price)
        
        # Update historical tracking
        imbalance = self.get_imbalance()
        if imbalance:
            self.spread_history.append(imbalance.spread)
            self.imbalance_history.append(imbalance.imbalance_ratio)
    
    def get_best_bid(self) -> Optional[float]:
        """Get best (highest) bid price"""
        return self.bids[0].price if self.bids else None
    
    def get_best_ask(self) -> Optional[float]:
        """Get best (lowest) ask price"""
        return self.asks[0].price if self.asks else None
    
    def get_mid_price(self) -> Optional[float]:
        """Get mid price (average of best bid and ask)"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        return None
    
    def get_spread(self) -> Optional[float]:
        """Get bid-ask spread"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return best_ask - best_bid
        return None
    
    def get_spread_bps(self) -> Optional[float]:
        """Get spread in basis points"""
        spread = self.get_spread()
        mid = self.get_mid_price()
        
        if spread and mid and mid > 0:
            return (spread / mid) * 10000
        return None
    
    def get_imbalance(self, levels: int = 10) -> Optional[OrderBookImbalance]:
        """
        Calculate order book imbalance
        
        Args:
            levels: Number of levels to include in calculation
            
        Returns:
            OrderBookImbalance object with metrics
        """
        if not self.bids or not self.asks:
            return None
        
        # Calculate total volume on each side
        bid_volume = sum(level.quantity for level in self.bids[:levels])
        ask_volume = sum(level.quantity for level in self.asks[:levels])
        
        # Calculate imbalance ratio
        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            imbalance_ratio = 0.0
        else:
            imbalance_ratio = (bid_volume - ask_volume) / total_volume
        
        # Get spread and mid price
        spread = self.get_spread() or 0.0
        mid_price = self.get_mid_price() or 0.0
        
        # Calculate liquidity score (0 to 1)
        # Higher volume and tighter spread = more liquid
        liquidity_score = min(1.0, total_volume / 10000)  # Normalize
        if spread > 0:
            liquidity_score *= (1.0 / (1.0 + spread))
        
        # Determine pressure direction
        if imbalance_ratio > 0.2:
            pressure = "BUY"
        elif imbalance_ratio < -0.2:
            pressure = "SELL"
        else:
            pressure = "NEUTRAL"
        
        return OrderBookImbalance(
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            imbalance_ratio=imbalance_ratio,
            spread=spread,
            mid_price=mid_price,
            liquidity_score=liquidity_score,
            pressure=pressure
        )
    
    def get_depth_at_price(self, price: float, side: str = "both") -> float:
        """
        Get total quantity available at or better than a price
        
        Args:
            price: Price level to check
            side: "buy" (bids >= price), "sell" (asks <= price), or "both"
            
        Returns:
            Total quantity available
        """
        depth = 0.0
        
        if side in ["buy", "both"]:
            # Sum bids at or above price
            depth += sum(level.quantity for level in self.bids if level.price >= price)
        
        if side in ["sell", "both"]:
            # Sum asks at or below price
            depth += sum(level.quantity for level in self.asks if level.price <= price)
        
        return depth
    
    def get_volume_weighted_price(self, side: str, levels: int = 10) -> Optional[float]:
        """
        Get volume-weighted average price for specified side
        
        Args:
            side: "bid" or "ask"
            levels: Number of levels to include
            
        Returns:
            Volume-weighted average price
        """
        if side == "bid":
            levels_to_use = self.bids[:levels]
        elif side == "ask":
            levels_to_use = self.asks[:levels]
        else:
            return None
        
        if not levels_to_use:
            return None
        
        total_value = sum(level.value for level in levels_to_use)
        total_volume = sum(level.quantity for level in levels_to_use)
        
        if total_volume == 0:
            return None
        
        return total_value / total_volume
    
    def detect_walls(self, threshold_multiplier: float = 3.0) -> Tuple[List[float], List[float]]:
        """
        Detect buy/sell walls (large orders that may act as support/resistance)
        
        Args:
            threshold_multiplier: How many times average size to be considered a wall
            
        Returns:
            Tuple of (bid_walls, ask_walls) as price levels
        """
        bid_walls = []
        ask_walls = []
        
        if not self.bids or not self.asks:
            return (bid_walls, ask_walls)
        
        # Calculate average size
        avg_bid_size = np.mean([level.quantity for level in self.bids])
        avg_ask_size = np.mean([level.quantity for level in self.asks])
        
        # Find bids larger than threshold
        for level in self.bids:
            if level.quantity > avg_bid_size * threshold_multiplier:
                bid_walls.append(level.price)
        
        # Find asks larger than threshold
        for level in self.asks:
            if level.quantity > avg_ask_size * threshold_multiplier:
                ask_walls.append(level.price)
        
        return (bid_walls, ask_walls)
    
    def detect_iceberg_orders(self, window: int = 20) -> List[Dict]:
        """
        Detect potential iceberg orders (large hidden orders)
        Identified by repeated fills at the same price level
        
        Args:
            window: Number of recent updates to analyze
            
        Returns:
            List of suspected iceberg order locations
        """
        # This would require trade-by-trade data
        # Placeholder for production implementation
        return []
    
    def get_liquidity_heatmap(self, price_range: float = 0.02) -> Dict[float, float]:
        """
        Create liquidity heatmap showing volume at each price level
        
        Args:
            price_range: Percentage range around mid price to include
            
        Returns:
            Dictionary mapping price to total volume
        """
        mid = self.get_mid_price()
        if not mid:
            return {}
        
        heatmap = {}
        
        # Add bid side
        for level in self.bids:
            if abs(level.price - mid) / mid <= price_range:
                heatmap[level.price] = level.quantity
        
        # Add ask side
        for level in self.asks:
            if abs(level.price - mid) / mid <= price_range:
                heatmap[level.price] = level.quantity
        
        return heatmap
    
    def get_market_depth_profile(self) -> Dict[str, float]:
        """
        Get comprehensive market depth statistics
        
        Returns:
            Dictionary with depth metrics
        """
        if not self.bids or not self.asks:
            return {}
        
        imbalance = self.get_imbalance(levels=20)
        spread_bps = self.get_spread_bps()
        
        # Calculate depth at various distances from mid
        mid = self.get_mid_price()
        if not mid:
            return {}
        
        depths = {}
        for pct in [0.001, 0.005, 0.01, 0.02]:  # 0.1%, 0.5%, 1%, 2%
            bid_depth = self.get_depth_at_price(mid * (1 - pct), side="buy")
            ask_depth = self.get_depth_at_price(mid * (1 + pct), side="sell")
            depths[f'depth_{pct*100}%'] = bid_depth + ask_depth
        
        return {
            'mid_price': mid,
            'spread_bps': spread_bps or 0.0,
            'bid_volume': imbalance.bid_volume if imbalance else 0.0,
            'ask_volume': imbalance.ask_volume if imbalance else 0.0,
            'imbalance': imbalance.imbalance_ratio if imbalance else 0.0,
            'liquidity_score': imbalance.liquidity_score if imbalance else 0.0,
            **depths
        }
    
    def is_spread_anomaly(self, threshold: float = 2.0) -> bool:
        """
        Detect if current spread is anomalous
        
        Args:
            threshold: Number of standard deviations from mean
            
        Returns:
            True if spread is anomalous
        """
        if len(self.spread_history) < 20:
            return False
        
        current_spread = self.get_spread()
        if not current_spread:
            return False
        
        mean_spread = np.mean(self.spread_history)
        std_spread = np.std(self.spread_history)
        
        if std_spread == 0:
            return False
        
        z_score = abs((current_spread - mean_spread) / std_spread)
        return z_score > threshold
    
    def get_order_flow_toxicity(self) -> float:
        """
        Calculate order flow toxicity (informed trading indicator)
        High toxicity = likely informed traders, risky to trade against
        
        Returns:
            Toxicity score 0 to 1
        """
        if len(self.imbalance_history) < 20:
            return 0.5  # Neutral
        
        # Calculate volatility of imbalances
        imbalance_vol = np.std(list(self.imbalance_history)[-20:])
        
        # Higher volatility in imbalances = more toxic flow
        toxicity = min(1.0, imbalance_vol / 0.5)  # Normalize
        
        return toxicity

