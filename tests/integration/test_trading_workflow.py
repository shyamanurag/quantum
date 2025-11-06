"""
Integration tests for complete trading workflow
"""
import pytest
import asyncio
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.strategies.enhancements.ml_regime_classifier import MLRegimeClassifier, RegimeFeatures
from src.strategies.enhancements.position_sizer import AdvancedPositionSizer
from src.strategies.enhancements.signal_scorer import SignalScorer
from src.strategies.enhancements.footprint_analyzer import FootprintAnalyzer
from tests.mocks.mock_binance import MockBinanceExchange


class TestTradingWorkflow:
    """
    Test complete trading workflow:
    1. Regime classification
    2. Signal scoring
    3. Position sizing
    4. Order execution
    """
    
    @pytest.fixture
    def mock_exchange(self):
        """Create mock exchange"""
        return MockBinanceExchange(starting_balance=100000.0)
    
    @pytest.fixture
    def regime_classifier(self):
        """Create regime classifier"""
        return MLRegimeClassifier()
    
    @pytest.fixture
    def signal_scorer(self):
        """Create signal scorer"""
        return SignalScorer(min_score_to_trade=70.0)
    
    @pytest.fixture
    def position_sizer(self):
        """Create position sizer"""
        return AdvancedPositionSizer(
            portfolio_value=100000.0,
            max_risk_per_trade_pct=0.02
        )
    
    @pytest.fixture
    def footprint_analyzer(self):
        """Create footprint analyzer"""
        return FootprintAnalyzer(bar_size_minutes=1)
    
    @pytest.mark.asyncio
    async def test_complete_buy_workflow(
        self,
        mock_exchange,
        regime_classifier,
        signal_scorer,
        position_sizer,
        footprint_analyzer
    ):
        """Test complete buy workflow"""
        
        symbol = "BTCUSDT"
        
        # Step 1: Classify regime
        features = RegimeFeatures(
            realized_vol_1h=0.20, realized_vol_4h=0.22, realized_vol_24h=0.25,
            vol_of_vol=0.03, volume_1h=1500000, volume_4h=4000000,
            volume_24h=12000000, volume_ratio=1.3, returns_1h=0.02,
            returns_4h=0.04, returns_24h=0.06, price_range_1h=0.012,
            spread_bps=4.5, order_book_imbalance=0.4, depth_imbalance=0.3,
            trade_aggression=0.70, large_trade_frequency=0.18
        )
        
        regime_id, regime_conf = regime_classifier.predict(features)
        print(f"Regime: {regime_classifier.get_regime_name(regime_id)} (confidence: {regime_conf:.2%})")
        
        # Don't trade in extreme volatility
        if regime_id == 3:  # EXTREME_VOLATILITY_CHAOS
            print("Skipping trade: extreme volatility")
            return
        
        # Step 2: Score signal
        signal_score = signal_scorer.score_signal(
            price_near_support_resistance=True,
            technical_indicators_aligned=True,
            pattern_detected=True,
            whale_activity_present=True,
            volume_above_average=2.5,
            order_book_imbalance=0.65,
            volatility_regime=regime_classifier.get_regime_name(regime_id),
            volatility_percentile=45,
            trend_strength=0.80,
            momentum_acceleration=0.50,
            risk_reward_ratio=2.8,
            stop_loss_distance_pct=0.012,
            market_liquidity_score=0.85,
            spread_quality=0.90
        )
        
        print(f"Signal Score: {signal_score.total_score:.1f}/100 ({signal_score.quality.value})")
        
        if not signal_score.trade_recommended:
            print("Skipping trade: signal score too low")
            return
        
        # Step 3: Calculate position size
        ticker = await mock_exchange.get_ticker_price(symbol)
        current_price = ticker['price']
        
        position = position_sizer.calculate_kelly_position(
            symbol=symbol,
            win_rate=0.58,
            avg_win=120,
            avg_loss=60,
            current_price=current_price,
            stop_loss_distance_pct=0.015
        )
        
        print(f"Position Size: ${position.recommended_size_usd:,.2f} ({position.recommended_size_base:.4f} BTC)")
        print(f"Max Loss: ${position.max_loss_usd:,.2f}")
        
        # Step 4: Execute order
        order = await mock_exchange.create_order(
            symbol=symbol,
            side='BUY',
            order_type='MARKET',
            quantity=position.recommended_size_base
        )
        
        print(f"Order executed: {order['orderId']} - {order['status']}")
        
        # Verify order was filled
        assert order['status'] == 'FILLED'
        assert float(order['executedQty']) == position.recommended_size_base
        
        # Verify balance updated
        btc_balance = mock_exchange.get_balance('BTC')
        assert btc_balance > 0
        
        print(f"BTC Balance after trade: {btc_balance:.4f}")
    
    @pytest.mark.asyncio
    async def test_workflow_with_poor_signal(
        self,
        mock_exchange,
        signal_scorer
    ):
        """Test that poor signals are rejected"""
        
        # Score a poor signal
        signal_score = signal_scorer.score_signal(
            price_near_support_resistance=False,
            technical_indicators_aligned=False,
            pattern_detected=False,
            whale_activity_present=False,
            volume_above_average=0.6,
            order_book_imbalance=0.2,
            volatility_regime='EXTREME',
            volatility_percentile=92,
            trend_strength=0.25,
            momentum_acceleration=-0.25,
            risk_reward_ratio=1.0,
            stop_loss_distance_pct=0.020,
            market_liquidity_score=0.45,
            spread_quality=0.55
        )
        
        # Should not trade
        assert signal_score.trade_recommended == False
        print("Poor signal correctly rejected")
    
    @pytest.mark.asyncio
    async def test_risk_limit_enforcement(
        self,
        mock_exchange,
        position_sizer
    ):
        """Test that risk limits are enforced"""
        
        symbol = "BTCUSDT"
        ticker = await mock_exchange.get_ticker_price(symbol)
        current_price = ticker['price']
        
        # Calculate position with high risk
        position = position_sizer.calculate_kelly_position(
            symbol=symbol,
            win_rate=0.55,
            avg_win=100,
            avg_loss=50,
            current_price=current_price,
            stop_loss_distance_pct=0.015
        )
        
        # Max loss should never exceed max_risk_per_trade_pct
        max_allowed_loss = position_sizer.portfolio_value * position_sizer.max_risk_per_trade_pct
        assert position.max_loss_usd <= max_allowed_loss
        
        print(f"Risk limit enforced: ${position.max_loss_usd:,.2f} <= ${max_allowed_loss:,.2f}")
    
    @pytest.mark.asyncio
    async def test_insufficient_balance_handling(
        self,
        mock_exchange
    ):
        """Test handling of insufficient balance"""
        
        symbol = "BTCUSDT"
        
        # Try to buy more than we can afford
        with pytest.raises(ValueError, match="Insufficient"):
            await mock_exchange.create_order(
                symbol=symbol,
                side='BUY',
                order_type='MARKET',
                quantity=10.0  # Way more than $100k can buy
            )
        
        print("Insufficient balance correctly caught")
    
    @pytest.mark.asyncio
    async def test_order_cancellation(
        self,
        mock_exchange
    ):
        """Test order cancellation"""
        
        symbol = "BTCUSDT"
        ticker = await mock_exchange.get_ticker_price(symbol)
        
        # Place limit order (won't fill immediately)
        order = await mock_exchange.create_order(
            symbol=symbol,
            side='BUY',
            order_type='LIMIT',
            quantity=0.1,
            price=ticker['price'] * 0.9  # 10% below market
        )
        
        order_id = str(order['orderId'])
        
        # Cancel order
        cancel_result = await mock_exchange.cancel_order(symbol, order_id)
        assert cancel_result['status'] == 'CANCELLED'
        
        # Verify order status
        order_status = await mock_exchange.get_order(symbol, order_id)
        assert order_status['status'] == 'CANCELLED'
        
        print("Order cancellation successful")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

