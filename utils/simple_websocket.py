import asyncio
import json
import time
from typing import Dict, Optional, Callable, Any, List
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from utils.logging import get_logger, TradingLoggerAdapter
from config.settings import Settings


class SimpleWebSocketClient:
    """Simplified WebSocket client for testing basic connectivity"""
    
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.logger: TradingLoggerAdapter = get_logger("simple_websocket")
        
        if testnet:
            self.base_url = "wss://fstream.binancefuture.com/ws/"
        else:
            self.base_url = "wss://fstream.binance.com/ws/"
        
        self.websocket = None
        self.connection_status = "disconnected"
        self.subscriptions: Dict[str, Callable] = {}
        self._running = False
    
    async def connect(self, streams: List[str]) -> bool:
        """Connect to WebSocket with specified streams"""
        try:
            # Create stream URL
            stream_names = "/".join(streams)
            url = f"{self.base_url}{stream_names}"
            
            self.logger.info(f"Connecting to {url}")
            
            # Connect to WebSocket
            self.websocket = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.connection_status = "connected"
            self.logger.info("WebSocket connected successfully")
            
            return True
            
        except Exception as e:
            self.connection_status = "failed"
            self.logger.error(f"WebSocket connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self._running = False
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.connection_status = "disconnected"
        self.logger.info("WebSocket disconnected")
    
    async def listen(self, message_handler: Optional[Callable] = None):
        """Listen for messages"""
        if not self.websocket:
            self.logger.error("WebSocket not connected")
            return
        
        self._running = True
        self.logger.info("Starting message listening...")
        
        try:
            while self._running:
                try:
                    # Receive message with timeout
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=30.0
                    )
                    
                    # Parse JSON message
                    data = json.loads(message)
                    
                    # Handle message
                    if message_handler:
                        await self._safe_call(message_handler, data)
                    else:
                        await self._default_message_handler(data)
                    
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await self.websocket.ping()
                    self.logger.debug("Sent ping to keep connection alive")
                    
                except ConnectionClosed:
                    self.logger.warning("WebSocket connection closed")
                    break
                    
        except Exception as e:
            self.logger.error(f"Error in message listening: {e}")
        
        finally:
            self.connection_status = "disconnected"
    
    async def _default_message_handler(self, data: Dict[str, Any]):
        """Default message handler for testing"""
        if "stream" in data:
            stream_name = data["stream"]
            stream_data = data.get("data", {})
            
            if "kline" in stream_name:
                kline = stream_data.get("k", {})
                symbol = kline.get("s")
                close_price = kline.get("c")
                is_closed = kline.get("x", False)
                
                if is_closed:
                    self.logger.info(f"Kline closed: {symbol} @ {close_price}")
            
            elif "markPrice" in stream_name:
                symbol = stream_data.get("s")
                mark_price = stream_data.get("p")
                funding_rate = stream_data.get("r")
                
                self.logger.info(f"Mark price: {symbol} @ {mark_price} (funding: {funding_rate})")
        
        else:
            self.logger.debug(f"Received message: {json.dumps(data, indent=2)}")
    
    async def _safe_call(self, func: Callable, *args, **kwargs):
        """Safely call a function with error handling"""
        try:
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Error in callback: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get connection status"""
        is_connected = False
        try:
            is_connected = self.websocket is not None and not self.websocket.closed
        except AttributeError:
            is_connected = self.websocket is not None
        
        return {
            "status": self.connection_status,
            "running": self._running,
            "testnet": self.testnet,
            "connected": is_connected
        }


# Test function
async def test_websocket_connection():
    """Test WebSocket connection"""
    client = SimpleWebSocketClient(testnet=True)
    
    # Test streams (1-minute kline for BTCUSDT)
    streams = ["btcusdt@kline_1m"]
    
    try:
        # Connect
        connected = await client.connect(streams)
        if not connected:
            return False
        
        print(f"✅ WebSocket connected: {client.get_status()}")
        
        # Listen for a few messages
        listen_task = asyncio.create_task(client.listen())
        
        # Run for 10 seconds
        await asyncio.sleep(10)
        
        # Disconnect
        await client.disconnect()
        
        # Cancel listen task
        listen_task.cancel()
        try:
            await listen_task
        except asyncio.CancelledError:
            pass
        
        print("✅ WebSocket test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_websocket_connection())