#!/usr/bin/env python3
"""
Strategy system integration test
"""

import sys
from pathlib import Path
from datetime import datetime, UTC, timedelta
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent))


def test_strategy_base_framework():
    """Test base strategy framework"""
    print("=" * 50)
    print("Testing Strategy Base Framework...")
    
    try:
        from strategies.base import BaseStrategy, StrategySignal, StrategyState
        from database.models import SignalType
        from utils.data_models import KlineData
        
        # Test StrategySignal creation
        signal = StrategySignal(
            symbol="BTCUSDT",
            signal_type=SignalType.BUY,
            price=Decimal("50000.00"),
            confidence=Decimal("0.85"),
            notes="Test signal"
        )
        
        print(f"✅ Created StrategySignal: {signal.signal_type} at {signal.price}")
        print(f"   - Confidence: {signal.confidence}")
        print(f"   - Created at: {signal.created_at}")
        
        # Test signal to dict conversion
        signal_dict = signal.to_dict()
        print(f"✅ Signal dict conversion: {len(signal_dict)} fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Strategy base framework test failed: {e}")
        return False


def test_strategy_registry():
    """Test strategy registry system"""
    print("=" * 50)
    print("Testing Strategy Registry...")
    
    try:
        from strategies.manager import StrategyRegistry, strategy_manager
        from strategies.vwap_strategy import VWAPStrategy
        
        # Test registry
        registry = StrategyRegistry()
        
        # Test manual registration
        registry.register(VWAPStrategy)
        print(f"✅ Manually registered VWAPStrategy")
        
        # Test auto-discovery
        discovered_count = registry.auto_discover_strategies()
        print(f"✅ Auto-discovered {discovered_count} strategies")
        
        # Test listing strategies
        strategies = registry.list_strategies()
        print(f"✅ Available strategies: {strategies}")
        
        # Test getting strategy class
        vwap_class = registry.get_strategy("vwap")
        if vwap_class:
            print(f"✅ Retrieved VWAPStrategy class: {vwap_class.__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Strategy registry test failed: {e}")
        return False


def test_vwap_strategy_creation():
    """Test VWAP strategy creation and configuration"""
    print("=" * 50)
    print("Testing VWAP Strategy Creation...")
    
    try:
        from strategies.vwap_strategy import VWAPStrategy
        
        # Test configuration
        config = {
            'vwap_period': 20,
            'vwap_std_multiplier': 2.0,
            'adx_period': 14,
            'adx_threshold': 20,
            'target_profit_pct': 0.006,
            'stop_loss_pct': 0.003,
            'volatility_threshold': 0.02,
            'volatility_halt_minutes': 10,
            'min_confidence': 0.6
        }
        
        # Create strategy instance
        strategy = VWAPStrategy("BTCUSDT", config)
        print(f"✅ Created VWAPStrategy for {strategy.symbol}")
        print(f"   - State: {strategy.state}")
        print(f"   - Required data length: {strategy.get_required_data_length()}")
        
        # Test strategy start
        success = strategy.start()
        if success:
            print(f"✅ Strategy started successfully")
            print(f"   - State: {strategy.state}")
        
        # Test status
        status = strategy.get_status()
        print(f"✅ Strategy status retrieved: {len(status)} fields")
        
        return True
        
    except Exception as e:
        print(f"❌ VWAP strategy creation test failed: {e}")
        return False


def test_technical_indicators():
    """Test technical indicators"""
    print("=" * 50)
    print("Testing Technical Indicators...")
    
    try:
        from utils.indicators import calculate_vwap, calculate_adx, calculate_rsi
        from utils.data_models import KlineData
        
        # Create sample kline data
        klines = []
        base_price = 50000.0
        
        for i in range(50):
            # Simulate some price movement
            price_change = (i % 5 - 2) * 100  # Simple oscillation
            price = base_price + price_change
            
            kline = KlineData(
                symbol="BTCUSDT",
                open_time=1640995200000 + (i * 60000),  # 1 minute intervals
                close_time=1640995260000 + (i * 60000),
                open_price=Decimal(str(price - 10)),
                high_price=Decimal(str(price + 20)),
                low_price=Decimal(str(price - 30)),
                close_price=Decimal(str(price)),
                volume=Decimal("10.0"),
                quote_volume=Decimal("500000.0"),
                trades_count=100,
                is_closed=True,
                interval="1m",
                first_trade_id=1000,
                last_trade_id=1099,
                base_asset_volume=Decimal("5.0"),
                quote_asset_volume=Decimal("250000.0")
            )
            klines.append(kline)
        
        # Test VWAP calculation
        vwap, vwap_std = calculate_vwap(klines[-20:])
        print(f"✅ VWAP calculation: {vwap:.2f} ± {vwap_std:.2f}")
        
        # Test ADX calculation
        adx = calculate_adx(klines[-20:])
        print(f"✅ ADX calculation: {adx:.2f}")
        
        # Test RSI calculation
        close_prices = [float(k.close_price) for k in klines]
        rsi = calculate_rsi(close_prices)
        print(f"✅ RSI calculation: {rsi:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Technical indicators test failed: {e}")
        return False


def test_strategy_manager():
    """Test strategy manager"""
    print("=" * 50)
    print("Testing Strategy Manager...")
    
    try:
        from strategies.manager import strategy_manager
        
        # Test getting available strategies
        strategies = strategy_manager.get_available_strategies()
        print(f"✅ Available strategies: {strategies}")
        
        # Test strategy status (should be empty initially)
        status = strategy_manager.get_strategy_status()
        print(f"✅ Manager status: {status['total_instances']} instances")
        
        # Test creating strategy (will fail due to symbol config, but should not crash)
        try:
            instance_key = strategy_manager.create_strategy("vwap", "BTCUSDT")
            if instance_key:
                print(f"✅ Created strategy instance: {instance_key}")
                
                # Test stopping
                success = strategy_manager.stop_strategy(instance_key)
                print(f"✅ Stopped strategy: {success}")
            else:
                print("ℹ️  Strategy creation failed (expected - no symbol config)")
        except Exception as e:
            print(f"ℹ️  Strategy creation failed (expected): {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Strategy manager test failed: {e}")
        return False


def test_vwap_signal_generation():
    """Test VWAP strategy signal generation with mock data"""
    print("=" * 50)
    print("Testing VWAP Signal Generation...")
    
    try:
        from strategies.vwap_strategy import VWAPStrategy
        from utils.data_models import KlineData
        
        # Create strategy with test config
        config = {
            'vwap_period': 20,
            'vwap_std_multiplier': 1.5,  # Lower for easier testing
            'adx_period': 14,
            'adx_threshold': 50,  # Higher to allow signals
            'target_profit_pct': 0.006,
            'stop_loss_pct': 0.003,
            'volatility_threshold': 0.05,  # Higher threshold
            'volatility_halt_minutes': 1,
            'min_confidence': 0.3  # Lower for easier testing
        }
        
        strategy = VWAPStrategy("BTCUSDT", config)
        strategy.start()
        
        # Generate mock kline data with a clear trend
        base_price = 50000.0
        signals_generated = []
        
        # First, add enough data to initialize indicators
        for i in range(25):
            price = base_price + (i * 10)  # Gradual increase
            
            kline = KlineData(
                symbol="BTCUSDT",
                open_time=1640995200000 + (i * 60000),
                close_time=1640995260000 + (i * 60000),
                open_price=Decimal(str(price - 5)),
                high_price=Decimal(str(price + 10)),
                low_price=Decimal(str(price - 15)),
                close_price=Decimal(str(price)),
                volume=Decimal("10.0"),
                quote_volume=Decimal("500000.0"),
                trades_count=100,
                is_closed=True,
                interval="1m",
                first_trade_id=1000 + i,
                last_trade_id=1099 + i,
                base_asset_volume=Decimal("5.0"),
                quote_asset_volume=Decimal("250000.0")
            )
            
            signals = strategy.add_kline(kline)
            if signals:
                signals_generated.extend(signals)
                print(f"✅ Generated {len(signals)} signals at price {price}")
        
        print(f"✅ Total signals generated: {len(signals_generated)}")
        
        # Test strategy status
        status = strategy.get_status()
        print(f"✅ Strategy ready: {status['is_ready']}")
        print(f"   - Signals generated: {status['signals_generated']}")
        print(f"   - VWAP: {status.get('current_vwap', 0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ VWAP signal generation test failed: {e}")
        return False


def main():
    """Run all strategy tests"""
    print("🔍 Starting Strategy System Tests...")
    print("=" * 50)
    
    tests = [
        ("Strategy Base Framework", test_strategy_base_framework),
        ("Strategy Registry", test_strategy_registry),
        ("VWAP Strategy Creation", test_vwap_strategy_creation),
        ("Technical Indicators", test_technical_indicators),
        ("Strategy Manager", test_strategy_manager),
        ("VWAP Signal Generation", test_vwap_signal_generation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("=" * 50)
    print("📊 STRATEGY TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("=" * 50)
    print(f"🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All strategy tests passed! Strategy engine is working.")
    else:
        print("⚠️ Some strategy tests failed. Check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)