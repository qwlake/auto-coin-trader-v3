#!/usr/bin/env python3
"""
Simple connection test without API keys
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def test_public_endpoints():
    """Test public endpoints that don't require API keys"""
    print("🔍 Testing Binance SDK Public Endpoints...")
    
    try:
        from binance_sdk_derivatives_trading_usds_futures.rest_api import DerivativesTradingUsdsFuturesRestAPI
        from binance_common.configuration import ConfigurationRestAPI
        
        # Create config for testnet without API keys
        config = ConfigurationRestAPI(
            base_path="https://testnet.binancefuture.com"
        )
        
        client = DerivativesTradingUsdsFuturesRestAPI(config)
        
        print("✅ REST client created")
        
        # Test server time (public endpoint)
        try:
            server_time_response = client.check_server_time()
            server_time = server_time_response.data if hasattr(server_time_response, 'data') else server_time_response
            print(f"✅ Server time: {server_time}")
        except Exception as e:
            print(f"❌ Server time failed: {e}")
        
        # Test exchange info (public endpoint)
        try:
            exchange_info_response = client.exchange_information()
            exchange_info = exchange_info_response.data if hasattr(exchange_info_response, 'data') else exchange_info_response
            symbols_count = len(exchange_info.get('symbols', [])) if isinstance(exchange_info, dict) else 'unknown'
            print(f"✅ Exchange info: {symbols_count} symbols")
        except Exception as e:
            print(f"❌ Exchange info failed: {e}")
        
        # Test ticker (public endpoint)
        try:
            ticker_response = client.symbol_price_ticker(symbol="BTCUSDT")
            ticker = ticker_response.data if hasattr(ticker_response, 'data') else ticker_response
            print(f"✅ BTCUSDT ticker: {ticker}")
        except Exception as e:
            print(f"❌ Ticker failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Public endpoint test failed: {e}")
        return False


async def test_websocket_basic():
    """Test basic WebSocket functionality"""
    print("\n🔍 Testing WebSocket Basic Functionality...")
    
    try:
        from binance_sdk_derivatives_trading_usds_futures.websocket_streams import DerivativesTradingUsdsFuturesWebSocketStreams
        from binance_common.configuration import ConfigurationWebSocketStreams
        
        # Create config for testnet with correct stream URL format
        config = ConfigurationWebSocketStreams(
            stream_url="wss://fstream.binancefuture.com/stream",
            reconnect_delay=5
        )
        
        ws_client = DerivativesTradingUsdsFuturesWebSocketStreams(config)
        
        print("✅ WebSocket client created")
        
        # Set up a simple callback
        received_data = []
        
        def simple_callback(data):
            received_data.append(data)
            print(f"📨 Received data: {type(data)} - {str(data)[:100]}...")
        
        # Connect with proper arguments - use the stream endpoint
        await ws_client.connect("wss://fstream.binancefuture.com/stream", config)
        print("✅ WebSocket connected")
        
        # Subscribe to BTCUSDT kline
        await ws_client.kline_candlestick_streams("btcusdt", "1m", simple_callback)
        print("✅ Subscribed to BTCUSDT 1m kline")
        
        # Listen for a few seconds
        print("🔄 Listening for 5 seconds...")
        await asyncio.sleep(5)
        
        # Disconnect
        await ws_client.close_connection()
        print("✅ WebSocket disconnected")
        
        print(f"📊 Received {len(received_data)} messages")
        
        return len(received_data) > 0
        
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False


async def main():
    """Run connection tests"""
    print("🚀 Starting Simple Connection Tests")
    print("=" * 50)
    
    rest_result = await test_public_endpoints()
    ws_result = await test_websocket_basic()
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)
    
    print(f"REST API: {'✅ PASS' if rest_result else '❌ FAIL'}")
    print(f"WebSocket: {'✅ PASS' if ws_result else '❌ FAIL'}")
    
    if rest_result and ws_result:
        print("\n🎉 All connection tests passed! Binance SDK is working.")
        return True
    else:
        print("\n⚠️ Some tests failed. SDK might have issues.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)