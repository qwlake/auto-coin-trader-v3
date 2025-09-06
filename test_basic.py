#!/usr/bin/env python3
"""
Basic integration test script to verify core functionality
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_config_loading():
    """Test configuration loading"""
    print("=" * 50)
    print("Testing Configuration Loading...")
    
    try:
        from config.settings import Settings
        
        # Test loading settings
        settings = Settings()
        print(f"✅ Settings loaded successfully")
        print(f"   - Mode: {settings.trading.mode}")
        print(f"   - Database URL: {settings.database.url}")
        print(f"   - Log Level: {settings.logging.level}")
        print(f"   - Streamlit Port: {settings.streamlit.port}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False


async def test_logging_system():
    """Test logging system"""
    print("=" * 50)
    print("Testing Logging System...")
    
    try:
        from utils.logging import setup_logging, get_logger, log_trade_activity
        
        # Setup logging
        logger = setup_logging(
            log_level="INFO",
            console_enabled=True,
            file_enabled=False,  # Don't create files for test
            json_format=True
        )
        
        # Get a logger
        test_logger = get_logger("test", {"test_id": "basic_test"})
        
        # Test logging
        test_logger.info("Test log message", extra_data={"test": True})
        
        # Test trade activity logging
        log_trade_activity(
            test_logger,
            "signal",
            "BTCUSDT",
            {"action": "BUY", "price": 50000, "quantity": 0.001},
            "INFO"
        )
        
        print("✅ Logging system working")
        return True
        
    except Exception as e:
        print(f"❌ Logging system failed: {e}")
        return False


async def test_data_models():
    """Test data models"""
    print("=" * 50)
    print("Testing Data Models...")
    
    try:
        from utils.data_models import KlineData, MarkPriceData, OrderData
        from decimal import Decimal
        
        # Test KlineData
        kline = KlineData(
            symbol="BTCUSDT",
            open_time=1640995200000,
            close_time=1640995260000,
            open_price=Decimal("50000.00"),
            high_price=Decimal("50100.00"),
            low_price=Decimal("49900.00"),
            close_price=Decimal("50050.00"),
            volume=Decimal("10.5"),
            quote_volume=Decimal("525525.00"),
            trades_count=100,
            is_closed=True,
            interval="1m",
            first_trade_id=1000,
            last_trade_id=1099,
            base_asset_volume=Decimal("5.25"),
            quote_asset_volume=Decimal("262762.50")
        )
        
        print(f"✅ KlineData created: {kline.symbol} at {kline.close_price}")
        print(f"   - Datetime: {kline.datetime}")
        print(f"   - Dict conversion: {kline.to_dict()['close']}")
        
        # Test MarkPriceData
        mark_price = MarkPriceData(
            symbol="BTCUSDT",
            mark_price=Decimal("50025.00"),
            index_price=Decimal("50020.00"),
            estimated_settle_price=Decimal("50022.00"),
            funding_rate=Decimal("0.0001"),
            next_funding_time=1641009600000,
            event_time=1640995260000
        )
        
        print(f"✅ MarkPriceData created: {mark_price.mark_price}")
        print(f"   - Funding rate: {mark_price.funding_rate}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data models failed: {e}")
        return False


async def test_symbol_config():
    """Test symbol configuration"""
    print("=" * 50)
    print("Testing Symbol Configuration...")
    
    try:
        from config.symbols import SymbolManager
        
        # Test symbol manager
        symbol_manager = SymbolManager()
        
        # Load existing BTCUSDT config
        btc_config = symbol_manager.load_symbol_config("BTCUSDT", "vwap")
        print(f"✅ Symbol config loaded: {btc_config.symbol}")
        print(f"   - Enabled: {btc_config.enabled}")
        print(f"   - Leverage: {btc_config.leverage}")
        print(f"   - Position size: {btc_config.position_size_usd}")
        
        # Test getting enabled symbols
        enabled_symbols = symbol_manager.get_enabled_symbols("vwap")
        print(f"✅ Enabled symbols: {enabled_symbols}")
        
        return True
        
    except Exception as e:
        print(f"❌ Symbol configuration failed: {e}")
        return False


async def test_precision_management():
    """Test precision management with mock data"""
    print("=" * 50)
    print("Testing Precision Management...")
    
    try:
        from utils.precision import ExchangeInfo, PrecisionManager
        from decimal import Decimal
        
        # Create mock exchange info
        exchange_info = ExchangeInfo()
        
        # Mock BTCUSDT exchange info
        mock_exchange_info = {
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                    "baseAssetPrecision": 8,
                    "quotePrecision": 8,
                    "pricePrecision": 2,
                    "quantityPrecision": 6,
                    "filters": [
                        {
                            "filterType": "LOT_SIZE",
                            "minQty": "0.000001",
                            "maxQty": "1000",
                            "stepSize": "0.000001"
                        },
                        {
                            "filterType": "PRICE_FILTER",
                            "minPrice": "0.01",
                            "maxPrice": "1000000",
                            "tickSize": "0.01"
                        },
                        {
                            "filterType": "MIN_NOTIONAL",
                            "minNotional": "10"
                        }
                    ]
                }
            ]
        }
        
        exchange_info.update_exchange_info(mock_exchange_info)
        precision_manager = PrecisionManager(exchange_info)
        
        # Test quantity rounding
        quantity = Decimal("0.0012345")
        rounded_qty = precision_manager.round_quantity("BTCUSDT", quantity)
        print(f"✅ Quantity rounding: {quantity} -> {rounded_qty}")
        
        # Test price rounding
        price = Decimal("50123.456")
        rounded_price = precision_manager.round_price("BTCUSDT", price)
        print(f"✅ Price rounding: {price} -> {rounded_price}")
        
        # Test validation
        is_valid, msg = precision_manager.validate_order("BTCUSDT", "BUY", "LIMIT", 
                                                        Decimal("0.001"), Decimal("50000"))
        print(f"✅ Order validation: {is_valid} - {msg}")
        
        return True
        
    except Exception as e:
        print(f"❌ Precision management failed: {e}")
        return False


async def test_data_validation():
    """Test data validation"""
    print("=" * 50)
    print("Testing Data Validation...")
    
    try:
        from utils.data_validation import DataValidator
        from utils.data_models import KlineData
        from decimal import Decimal
        
        validator = DataValidator("BTCUSDT")
        
        # Create valid kline
        valid_kline = KlineData(
            symbol="BTCUSDT",
            open_time=1640995200000,
            close_time=1640995260000,
            open_price=Decimal("50000.00"),
            high_price=Decimal("50100.00"),
            low_price=Decimal("49900.00"),
            close_price=Decimal("50050.00"),
            volume=Decimal("10.5"),
            quote_volume=Decimal("525525.00"),
            trades_count=100,
            is_closed=True,
            interval="1m",
            first_trade_id=1000,
            last_trade_id=1099,
            base_asset_volume=Decimal("5.25"),
            quote_asset_volume=Decimal("262762.50")
        )
        
        is_valid, errors = validator.validate_kline(valid_kline)
        print(f"✅ Kline validation: {is_valid}")
        if errors:
            print(f"   - Errors: {errors}")
        
        # Get validation stats
        stats = validator.get_validation_stats()
        print(f"✅ Validation stats: {stats['total_validated']} validated, {stats['validation_errors']} errors")
        
        return True
        
    except Exception as e:
        print(f"❌ Data validation failed: {e}")
        return False


async def test_database_basic():
    """Test basic database functionality"""
    print("=" * 50)
    print("Testing Database Basic Functionality...")
    
    try:
        from config.settings import Settings
        from database.connection import initialize_database, get_database_manager
        from database.operations import db_ops
        from database.models import OrderSide, OrderType, OrderStatus, SignalType
        from decimal import Decimal
        
        settings = Settings()
        
        # Initialize database
        success = initialize_database(settings)
        if not success:
            print("❌ Database initialization failed")
            return False
        
        # Test database health
        db_manager = get_database_manager(settings)
        health = db_manager.health_check()
        
        if not health:
            print("❌ Database health check failed")
            return False
        
        print("✅ Database initialized and healthy")
        
        # Test basic operations
        with db_manager.get_session() as session:
            # Test creating a simple signal
            signal_data = {
                "strategy": "test_strategy",
                "symbol": "BTCUSDT", 
                "signal_type": SignalType.BUY,
                "price": Decimal("50000.00"),
                "confidence": Decimal("0.85")
            }
            
            signal = db_ops.signals.create_signal(session, signal_data)
            print(f"✅ Created test signal: ID {signal.id}")
            
            # Test retrieving signals
            signals = db_ops.signals.get_recent_signals(session, limit=1)
            print(f"✅ Retrieved {len(signals)} signals")
        
        return True
        
    except Exception as e:
        print(f"❌ Database basic test failed: {e}")
        return False


async def test_strategy_basic():
    """Test basic strategy functionality"""
    print("=" * 50)
    print("Testing Strategy Engine Basic Functionality...")
    
    try:
        from strategies.base import BaseStrategy, StrategySignal, StrategyState
        from strategies.manager import StrategyRegistry, strategy_manager
        from strategies.vwap_strategy import VWAPStrategy
        from database.models import SignalType
        from utils.indicators import calculate_vwap, calculate_adx
        from decimal import Decimal
        
        # Test strategy signal creation
        signal = StrategySignal(
            symbol="BTCUSDT",
            signal_type=SignalType.BUY,
            price=Decimal("50000.00"),
            confidence=Decimal("0.85")
        )
        print("✅ Created strategy signal")
        
        # Test strategy registry
        registry = StrategyRegistry()
        registry.register(VWAPStrategy)
        strategies = registry.list_strategies()
        print(f"✅ Strategy registry: {len(strategies)} strategies")
        
        # Test VWAP strategy creation
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
        
        strategy = VWAPStrategy("BTCUSDT", config)
        success = strategy.start()
        print(f"✅ VWAP strategy started: {success}")
        
        # Test strategy manager
        available = strategy_manager.get_available_strategies()
        print(f"✅ Strategy manager: {len(available)} available strategies")
        
        return True
        
    except Exception as e:
        print(f"❌ Strategy engine basic test failed: {e}")
        return False


async def test_imports():
    """Test that all modules can be imported"""
    print("=" * 50)
    print("Testing Module Imports...")
    
    modules_to_test = [
        ("config.settings", "Settings"),
        ("config.symbols", "SymbolManager"),
        ("config.api_keys", "APIKeyManager"),
        ("utils.logging", "setup_logging"),
        ("utils.data_models", "KlineData"),
        ("utils.precision", "PrecisionManager"),
        ("utils.data_validation", "DataValidator"),
        ("utils.binance_websocket", "BinanceWebSocketClient"),
        ("utils.binance_rest", "BinanceRestClient"),
        ("database.connection", "DatabaseManager"),
        ("database.models", "Order"),
        ("database.operations", "DatabaseOperations"),
        ("strategies.base", "BaseStrategy"),
        ("strategies.vwap_strategy", "VWAPStrategy"),
        ("strategies.manager", "StrategyManager"),
        ("utils.indicators", "calculate_vwap")
    ]
    
    failed_imports = []
    
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
        except Exception as e:
            print(f"❌ {module_name}.{class_name}: {e}")
            failed_imports.append((module_name, class_name, str(e)))
    
    if failed_imports:
        print(f"\n❌ Failed imports: {len(failed_imports)}")
        for module_name, class_name, error in failed_imports:
            print(f"   - {module_name}.{class_name}: {error}")
        return False
    else:
        print(f"\n✅ All {len(modules_to_test)} modules imported successfully")
        return True


async def main():
    """Run all tests"""
    print("🔍 Starting Basic Integration Tests...")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Configuration Loading", test_config_loading),
        ("Logging System", test_logging_system),
        ("Data Models", test_data_models),
        ("Symbol Configuration", test_symbol_config),
        ("Precision Management", test_precision_management),
        ("Data Validation", test_data_validation),
        ("Database Basic", test_database_basic),
        ("Strategy Engine Basic", test_strategy_basic),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("=" * 50)
    print(f"🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Core functionality is working.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())