import asyncio
import json
import time
from typing import Dict, Optional, Callable, Any, List
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from binance_common.websocket.websocket_api import BinanceWebSocketApiManager

from utils.logging import get_logger, TradingLoggerAdapter
from config.settings import Settings


class WebSocketClient:
    def __init__(self, settings: Settings, testnet: bool = True):
        self.settings = settings
        self.testnet = testnet
        self.logger: TradingLoggerAdapter = get_logger("websocket")
        
        self.ws_manager = None
        self.subscriptions: Dict[str, Callable] = {}
        self.connection_status = "disconnected"
        self.last_ping_time = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.base_backoff = 1
        self.max_backoff = settings.trading.ws_max_backoff_sec
        
        self._running = False
        self._health_task = None
        
    async def connect(self) -> bool:
        try:
            self.logger.info("Connecting to Binance WebSocket...")
            
            if self.testnet:
                base_url = "wss://fstream.binancefuture.com"
            else:
                base_url = "wss://fstream.binance.com"
            
            self.ws_manager = BinanceWebSocketApiManager(
                exchange="binance.com-futures",
                output_default="UnicornFy",
                enable_stream_signal_buffer=True
            )
            
            self.connection_status = "connected"
            self.reconnect_attempts = 0
            self.last_ping_time = time.time()
            
            self.logger.info("WebSocket connected successfully", 
                           extra_data={"testnet": self.testnet})
            
            return True
            
        except Exception as e:
            self.connection_status = "failed"
            self.logger.error(f"WebSocket connection failed: {e}", 
                            extra_data={"error": str(e)})
            return False
    
    async def disconnect(self):
        self._running = False
        
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        
        if self.ws_manager:
            self.ws_manager.stop_manager_with_all_streams()
            self.ws_manager = None
        
        self.connection_status = "disconnected"
        self.logger.info("WebSocket disconnected")
    
    def subscribe_kline(self, symbol: str, interval: str, callback: Callable) -> bool:
        if not self.ws_manager:
            self.logger.error("WebSocket not connected")
            return False
        
        try:
            stream_id = f"{symbol.lower()}@kline_{interval}"
            
            self.ws_manager.create_stream(
                channels=[stream_id],
                markets=[symbol],
                stream_label=f"kline_{symbol}_{interval}",
                stream_buffer_name=stream_id
            )
            
            self.subscriptions[stream_id] = callback
            
            self.logger.info(f"Subscribed to kline stream", 
                           extra_data={"symbol": symbol, "interval": interval})
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to kline stream: {e}",
                            extra_data={"symbol": symbol, "interval": interval, "error": str(e)})
            return False
    
    def subscribe_mark_price(self, symbol: str, callback: Callable) -> bool:
        if not self.ws_manager:
            self.logger.error("WebSocket not connected")
            return False
        
        try:
            stream_id = f"{symbol.lower()}@markPrice"
            
            self.ws_manager.create_stream(
                channels=[stream_id],
                markets=[symbol],
                stream_label=f"markPrice_{symbol}",
                stream_buffer_name=stream_id
            )
            
            self.subscriptions[stream_id] = callback
            
            self.logger.info(f"Subscribed to mark price stream", 
                           extra_data={"symbol": symbol})
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to mark price stream: {e}",
                            extra_data={"symbol": symbol, "error": str(e)})
            return False
    
    def subscribe_user_data(self, listen_key: str, callback: Callable) -> bool:
        if not self.ws_manager:
            self.logger.error("WebSocket not connected")
            return False
        
        try:
            self.ws_manager.create_stream(
                channels=[listen_key],
                stream_label="user_data",
                stream_buffer_name="user_data"
            )
            
            self.subscriptions["user_data"] = callback
            
            self.logger.info("Subscribed to user data stream")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to user data stream: {e}",
                            extra_data={"error": str(e)})
            return False
    
    async def start_message_processing(self):
        self._running = True
        self._health_task = asyncio.create_task(self._health_monitor())
        
        while self._running:
            try:
                if not self.ws_manager:
                    await asyncio.sleep(1)
                    continue
                
                oldest_data_from_stream_buffer = self.ws_manager.pop_stream_data_from_stream_buffer()
                
                if oldest_data_from_stream_buffer:
                    await self._process_message(oldest_data_from_stream_buffer)
                else:
                    await asyncio.sleep(0.01)
                    
            except Exception as e:
                self.logger.error(f"Error processing WebSocket messages: {e}",
                                extra_data={"error": str(e)})
                await asyncio.sleep(1)
    
    async def _process_message(self, message: Dict[str, Any]):
        try:
            if not message or "stream" not in message:
                return
            
            stream_id = message.get("stream", "")
            data = message.get("data", {})
            
            if stream_id in self.subscriptions:
                callback = self.subscriptions[stream_id]
                await self._safe_callback(callback, data)
            elif "user_data" in self.subscriptions and stream_id == "":
                callback = self.subscriptions["user_data"]
                await self._safe_callback(callback, data)
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}",
                            extra_data={"message": message, "error": str(e)})
    
    async def _safe_callback(self, callback: Callable, data: Dict[str, Any]):
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            self.logger.error(f"Error in callback: {e}",
                            extra_data={"data": data, "error": str(e)})
    
    async def _health_monitor(self):
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if self.ws_manager and self.connection_status == "connected":
                    # Update ping time
                    self.last_ping_time = time.time()
                    
                    # Check stream status
                    stream_info = self.ws_manager.get_stream_info()
                    if stream_info:
                        self.logger.debug("WebSocket health check passed",
                                        extra_data={"active_streams": len(stream_info)})
                    else:
                        self.logger.warning("No active streams detected")
                        
                elif self.connection_status == "failed" and self._running:
                    await self._attempt_reconnect()
                    
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}",
                                extra_data={"error": str(e)})
    
    async def _attempt_reconnect(self):
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error("Max reconnection attempts reached, stopping")
            self._running = False
            return
        
        self.reconnect_attempts += 1
        backoff_time = min(self.base_backoff * (2 ** (self.reconnect_attempts - 1)), self.max_backoff)
        
        self.logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}",
                        extra_data={"backoff_seconds": backoff_time})
        
        await asyncio.sleep(backoff_time)
        
        if await self.connect():
            # Resubscribe to all previous subscriptions
            await self._resubscribe_all()
    
    async def _resubscribe_all(self):
        subscriptions_copy = self.subscriptions.copy()
        self.subscriptions.clear()
        
        for stream_id, callback in subscriptions_copy.items():
            if "kline" in stream_id:
                parts = stream_id.split("@kline_")
                if len(parts) == 2:
                    symbol = parts[0].upper()
                    interval = parts[1]
                    self.subscribe_kline(symbol, interval, callback)
            elif "markPrice" in stream_id:
                symbol = stream_id.split("@")[0].upper()
                self.subscribe_mark_price(symbol, callback)
            elif stream_id == "user_data":
                # User data stream requires new listen key
                self.logger.warning("User data stream requires manual resubscription with new listen key")
    
    def get_connection_status(self) -> Dict[str, Any]:
        return {
            "status": self.connection_status,
            "last_ping": self.last_ping_time,
            "reconnect_attempts": self.reconnect_attempts,
            "active_subscriptions": len(self.subscriptions),
            "testnet": self.testnet
        }