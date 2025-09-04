import asyncio
import json
from typing import Dict, Any, Callable, Optional
from datetime import datetime

from binance_sdk_derivatives_trading_usds_futures.websocket_streams import DerivativesTradingUsdsFuturesWebSocketStreams
from binance_common.configuration import ConfigurationWebSocketStreams
from utils.logging import get_logger, TradingLoggerAdapter


class BinanceWebSocketClient:
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.logger: TradingLoggerAdapter = get_logger("binance_websocket")
        
        # Set up configuration
        if testnet:
            stream_url = "wss://fstream.binancefuture.com/stream"
        else:
            stream_url = "wss://fstream.binance.com/stream"
            
        self.config = ConfigurationWebSocketStreams(
            stream_url=stream_url,
            reconnect_delay=5
        )
        
        self.ws_client = None
        self.connection_status = "disconnected"
        self.message_handlers: Dict[str, Callable] = {}
        
    async def connect(self) -> bool:
        """Connect to Binance WebSocket"""
        try:
            self.logger.info("Connecting to Binance WebSocket...")
            
            # Initialize WebSocket client
            self.ws_client = DerivativesTradingUsdsFuturesWebSocketStreams(self.config)
            
            # Connect with proper arguments
            await self.ws_client.connect(self.config.stream_url, self.config)
            
            self.connection_status = "connected"
            self.logger.info("WebSocket connected successfully")
            
            return True
            
        except Exception as e:
            self.connection_status = "failed"
            self.logger.error(f"WebSocket connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.ws_client:
            await self.ws_client.close_connection()
            self.ws_client = None
        
        self.connection_status = "disconnected"
        self.logger.info("WebSocket disconnected")
    
    async def subscribe_kline(self, symbol: str, interval: str = "1m", callback: Optional[Callable] = None):
        """Subscribe to kline/candlestick streams"""
        try:
            if not self.ws_client:
                self.logger.error("WebSocket not connected")
                return False
            
            # Subscribe to kline stream
            await self.ws_client.kline_candlestick_streams(
                symbol=symbol.lower(),
                interval=interval,
                callback=callback or self._default_kline_handler
            )
            
            self.logger.info(f"Subscribed to kline stream: {symbol}@{interval}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to kline: {e}")
            return False
    
    async def subscribe_mark_price(self, symbol: str, callback: Optional[Callable] = None):
        """Subscribe to mark price stream"""
        try:
            if not self.ws_client:
                self.logger.error("WebSocket not connected")
                return False
            
            # Subscribe to mark price stream
            await self.ws_client.mark_price_stream(
                symbol=symbol.lower(),
                callback=callback or self._default_mark_price_handler
            )
            
            self.logger.info(f"Subscribed to mark price stream: {symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to mark price: {e}")
            return False
    
    def subscribe_user_data(self, listen_key: str, callback: Optional[Callable] = None):
        """Subscribe to user data stream"""
        try:
            if not self.ws_client:
                self.logger.error("WebSocket not connected")
                return False
            
            # Subscribe to user data stream
            self.ws_client.user_data(
                listen_key=listen_key,
                callback=callback or self._default_user_data_handler
            )
            
            self.logger.info("Subscribed to user data stream")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to user data: {e}")
            return False
    
    def _default_kline_handler(self, data: Dict[str, Any]):
        """Default kline data handler"""
        try:
            kline = data.get("k", {})
            symbol = kline.get("s")
            close_price = kline.get("c")
            volume = kline.get("v")
            is_closed = kline.get("x", False)
            
            if is_closed:
                self.logger.info(
                    f"Kline closed: {symbol} @ {close_price} (Vol: {volume})",
                    extra_data={
                        "symbol": symbol,
                        "price": close_price,
                        "volume": volume,
                        "is_closed": is_closed
                    }
                )
        except Exception as e:
            self.logger.error(f"Error handling kline data: {e}")
    
    def _default_mark_price_handler(self, data: Dict[str, Any]):
        """Default mark price handler"""
        try:
            symbol = data.get("s")
            mark_price = data.get("p")
            funding_rate = data.get("r")
            
            # Log every 10th update to reduce noise
            if hasattr(self, '_mark_price_count'):
                self._mark_price_count += 1
            else:
                self._mark_price_count = 1
            
            if self._mark_price_count % 10 == 0:
                self.logger.info(
                    f"Mark price: {symbol} @ {mark_price} (Funding: {funding_rate})",
                    extra_data={
                        "symbol": symbol,
                        "mark_price": mark_price,
                        "funding_rate": funding_rate
                    }
                )
        except Exception as e:
            self.logger.error(f"Error handling mark price data: {e}")
    
    def _default_user_data_handler(self, data: Dict[str, Any]):
        """Default user data handler"""
        try:
            event_type = data.get("e")
            
            if event_type == "ACCOUNT_UPDATE":
                self.logger.info("Account update received")
            elif event_type == "ORDER_TRADE_UPDATE":
                order = data.get("o", {})
                symbol = order.get("s")
                side = order.get("S")
                status = order.get("X")
                
                self.logger.info(
                    f"Order update: {symbol} {side} - {status}",
                    extra_data={
                        "symbol": symbol,
                        "side": side,
                        "status": status,
                        "event_type": event_type
                    }
                )
            else:
                self.logger.info(f"User data event: {event_type}")
                
        except Exception as e:
            self.logger.error(f"Error handling user data: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get connection status"""
        return {
            "status": self.connection_status,
            "connected": self.ws_client is not None,
            "testnet": self.testnet
        }


# Test function
async def test_binance_websocket():
    """Test Binance WebSocket connection"""
    client = BinanceWebSocketClient(testnet=True)
    
    try:
        # Connect
        connected = await client.connect()
        if not connected:
            print("❌ Failed to connect to WebSocket")
            return False
        
        print(f"✅ Connected: {client.get_status()}")
        
        # Subscribe to BTCUSDT kline
        await client.subscribe_kline("BTCUSDT", "1m")
        
        # Subscribe to BTCUSDT mark price
        await client.subscribe_mark_price("BTCUSDT")
        
        print("✅ Subscribed to streams, listening for 10 seconds...")
        
        # Listen for messages
        await asyncio.sleep(10)
        
        # Disconnect
        await client.disconnect()
        
        print("✅ WebSocket test completed")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_binance_websocket())