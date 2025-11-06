"""
Unit tests for footprint analyzer
"""
import pytest
import asyncio
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.strategies.enhancements.footprint_analyzer import FootprintAnalyzer


class TestFootprintAnalyzer:
    """Test footprint analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return FootprintAnalyzer(bar_size_minutes=1, price_tick_size=0.1)
    
    @pytest.mark.asyncio
    async def test_initialization(self, analyzer):
        """Test analyzer initializes correctly"""
        assert analyzer.bar_size_minutes == 1
        assert analyzer.price_tick_size == 0.1
    
    @pytest.mark.asyncio
    async def test_add_trade(self, analyzer):
        """Test adding trades to footprint"""
        timestamp = datetime.utcnow()
        
        # Add buy trade
        await analyzer.add_trade(
            symbol="BTCUSDT",
            price=45000.0,
            volume=1.5,
            side='BUY',
            timestamp=timestamp
        )
        
        # Check current bar exists
        assert "BTCUSDT" in analyzer.current_bars
        bar = analyzer.current_bars["BTCUSDT"]
        assert bar.close == 45000.0
        assert bar.total_ask_volume == 1.5
    
    @pytest.mark.asyncio
    async def test_delta_calculation(self, analyzer):
        """Test delta calculation"""
        timestamp = datetime.utcnow()
        symbol = "BTCUSDT"
        
        # Add buy trades
        await analyzer.add_trade(symbol, 45000.0, 2.0, 'BUY', timestamp)
        await analyzer.add_trade(symbol, 45001.0, 1.0, 'BUY', timestamp)
        
        # Add sell trades
        await analyzer.add_trade(symbol, 45000.0, 0.5, 'SELL', timestamp)
        
        # Delta should be positive (more buying)
        delta = analyzer.get_current_delta(symbol)
        assert delta > 0
    
    @pytest.mark.asyncio
    async def test_bar_closure(self, analyzer):
        """Test bar closure after time window"""
        timestamp1 = datetime.utcnow()
        timestamp2 = timestamp1 + timedelta(minutes=2)  # 2 minutes later
        
        symbol = "BTCUSDT"
        
        # First trade
        await analyzer.add_trade(symbol, 45000.0, 1.0, 'BUY', timestamp1)
        
        # Second trade (should close first bar)
        await analyzer.add_trade(symbol, 45100.0, 1.0, 'BUY', timestamp2)
        
        # Should have bars stored
        assert symbol in analyzer.bars
        assert len(analyzer.bars[symbol]) > 0
    
    @pytest.mark.asyncio
    async def test_point_of_control(self, analyzer):
        """Test POC calculation"""
        timestamp = datetime.utcnow()
        symbol = "BTCUSDT"
        
        # Add multiple trades at different prices
        await analyzer.add_trade(symbol, 45000.0, 1.0, 'BUY', timestamp)
        await analyzer.add_trade(symbol, 45000.0, 2.0, 'BUY', timestamp)  # Most volume here
        await analyzer.add_trade(symbol, 45100.0, 0.5, 'BUY', timestamp)
        
        # Close bar
        timestamp2 = timestamp + timedelta(minutes=2)
        await analyzer.add_trade(symbol, 45100.0, 0.1, 'BUY', timestamp2)
        
        poc = analyzer.get_point_of_control(symbol, lookback_bars=1)
        # POC should be at 45000 (highest volume)
        assert poc is not None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

