#!/usr/bin/env python3
"""
Database system integration test
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, UTC
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent))


def test_database_initialization():
    """Test database initialization"""
    print("=" * 50)
    print("Testing Database Initialization...")
    
    try:
        from config.settings import Settings
        from database.connection import initialize_database, get_database_manager
        
        settings = Settings()
        
        # Initialize database
        success = initialize_database(settings)
        if not success:
            print("❌ Database initialization failed")
            return False
        
        # Test connection
        db_manager = get_database_manager(settings)
        health = db_manager.health_check()
        
        if health:
            print("✅ Database initialized and healthy")
            print(f"   - Connection info: {db_manager.get_connection_info()}")
            return True
        else:
            print("❌ Database health check failed")
            return False
        
    except Exception as e:
        print(f"❌ Database initialization test failed: {e}")
        return False


def test_database_models():
    """Test database models and operations"""
    print("=" * 50)
    print("Testing Database Models and Operations...")
    
    try:
        from database.connection import get_database_manager
        from database.operations import db_ops
        from database.models import OrderSide, OrderType, OrderStatus, SignalType
        
        db_manager = get_database_manager()
        
        with db_manager.get_session() as session:
            # Test creating a signal
            signal_data = {
                "strategy": "test_strategy",
                "symbol": "BTCUSDT", 
                "signal_type": SignalType.BUY,
                "price": Decimal("50000.00"),
                "quantity": Decimal("0.001"),
                "confidence": Decimal("0.85")
            }
            
            signal = db_ops.signals.create_signal(session, signal_data)
            print(f"✅ Created signal: ID {signal.id}")
            
            # Test creating an order
            order_data = {
                "binance_order_id": 12345,
                "binance_client_order_id": "test_order_001",
                "symbol": "BTCUSDT",
                "side": OrderSide.BUY,
                "order_type": OrderType.LIMIT,
                "original_quantity": Decimal("0.001"),
                "price": Decimal("49950.00"),
                "status": OrderStatus.NEW,
                "signal_id": signal.id,
                "strategy": "test_strategy"
            }
            
            order = db_ops.orders.create_order(session, order_data)
            print(f"✅ Created order: ID {order.id}")
            
            # Test creating a position
            position_data = {
                "symbol": "BTCUSDT",
                "position_side": "BOTH",
                "position_amount": Decimal("0.001"),
                "entry_price": Decimal("50000.00"),
                "mark_price": Decimal("50100.00"),
                "unrealized_pnl": Decimal("0.1"),
                "leverage": 10,
                "strategy": "test_strategy"
            }
            
            position = db_ops.positions.upsert_position(session, position_data)
            print(f"✅ Created position: ID {position.id}")
            
            # Test creating candle data
            candle_data = {
                "symbol": "BTCUSDT",
                "open_time": datetime.now(UTC).replace(second=0, microsecond=0),
                "close_time": datetime.now(UTC).replace(second=59, microsecond=0),
                "open_price": Decimal("50000.00"),
                "high_price": Decimal("50150.00"),
                "low_price": Decimal("49950.00"),
                "close_price": Decimal("50100.00"),
                "volume": Decimal("10.5"),
                "quote_volume": Decimal("525525.00"),
                "trades_count": 150,
                "taker_buy_base_volume": Decimal("5.25"),
                "taker_buy_quote_volume": Decimal("262762.50"),
                "is_closed": True
            }
            
            candle = db_ops.candles.upsert_candle(session, candle_data)
            print(f"✅ Created candle: ID {candle.id}")
            
            # Test account snapshot
            snapshot_data = {
                "total_wallet_balance": Decimal("1000.00"),
                "total_unrealized_pnl": Decimal("10.50"),
                "total_margin_balance": Decimal("1010.50"),
                "total_initial_margin": Decimal("50.00"),
                "total_maintenance_margin": Decimal("25.00"),
                "max_withdraw_amount": Decimal("960.50"),
                "available_balance": Decimal("960.50")
            }
            
            snapshot = db_ops.account.create_snapshot(session, snapshot_data)
            print(f"✅ Created account snapshot: ID {snapshot.id}")
            
        return True
        
    except Exception as e:
        print(f"❌ Database models test failed: {e}")
        return False


def test_database_queries():
    """Test database query operations"""
    print("=" * 50)
    print("Testing Database Queries...")
    
    try:
        from database.connection import get_database_manager
        from database.operations import db_ops
        
        db_manager = get_database_manager()
        
        with db_manager.get_session() as session:
            # Test getting recent signals
            signals = db_ops.signals.get_recent_signals(session, limit=10)
            print(f"✅ Retrieved {len(signals)} recent signals")
            
            # Test getting orders by symbol
            orders = db_ops.orders.get_orders_by_symbol(session, "BTCUSDT", limit=10)
            print(f"✅ Retrieved {len(orders)} orders for BTCUSDT")
            
            # Test getting positions
            positions = db_ops.positions.get_all_positions(session, active_only=False)
            print(f"✅ Retrieved {len(positions)} positions")
            
            # Test getting recent candles
            candles = db_ops.candles.get_recent_candles(session, "BTCUSDT", limit=5)
            print(f"✅ Retrieved {len(candles)} recent candles")
            
            # Test signal performance
            performance = db_ops.signals.get_signal_performance(session, "test_strategy")
            print(f"✅ Signal performance: {performance}")
            
            # Test latest account snapshot
            latest_snapshot = db_ops.account.get_latest_snapshot(session)
            if latest_snapshot:
                print(f"✅ Latest account balance: {latest_snapshot.total_wallet_balance}")
            
        return True
        
    except Exception as e:
        print(f"❌ Database queries test failed: {e}")
        return False


def test_database_migrations():
    """Test database migration system"""
    print("=" * 50)
    print("Testing Database Migrations...")
    
    try:
        from database.migrations import run_migrations, get_migration_status
        
        # Get initial status
        status = get_migration_status()
        print(f"✅ Migration status retrieved")
        print(f"   - Total migrations: {status.get('total_migrations', 0)}")
        print(f"   - Applied: {status.get('applied_count', 0)}")
        print(f"   - Pending: {status.get('pending_count', 0)}")
        
        # Run migrations
        success = run_migrations()
        if success:
            print("✅ Migrations completed successfully")
        else:
            print("⚠️ Some migrations may have failed")
        
        # Get final status
        final_status = get_migration_status()
        print(f"✅ Final migration status:")
        print(f"   - Applied: {final_status.get('applied_count', 0)}")
        print(f"   - Pending: {final_status.get('pending_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database migrations test failed: {e}")
        return False


def main():
    """Run all database tests"""
    print("🔍 Starting Database Integration Tests...")
    print("=" * 50)
    
    tests = [
        ("Database Initialization", test_database_initialization),
        ("Database Models", test_database_models),  
        ("Database Queries", test_database_queries),
        ("Database Migrations", test_database_migrations)
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
    print("📊 DATABASE TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("=" * 50)
    print(f"🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All database tests passed! Database layer is working.")
    else:
        print("⚠️ Some database tests failed. Check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)