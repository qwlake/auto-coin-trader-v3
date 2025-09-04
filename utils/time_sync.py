import asyncio
import time
from typing import Optional
from datetime import datetime

import aiohttp
from binance_common.rest.futures_api import BinanceFuturesRestApiManager

from utils.logging import get_logger, TradingLoggerAdapter


class TimeSynchronizer:
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.logger: TradingLoggerAdapter = get_logger("time_sync")
        
        self._time_offset: Optional[int] = None  # Offset in milliseconds
        self._last_sync_time: Optional[float] = None
        self._sync_interval = 300  # Sync every 5 minutes
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Binance server time endpoints
        if testnet:
            self.server_time_url = "https://testnet.binancefuture.com/fapi/v1/time"
        else:
            self.server_time_url = "https://fapi.binance.com/fapi/v1/time"
    
    async def start_sync(self):
        """Start the time synchronization service"""
        if self._running:
            return
        
        self.logger.info("Starting time synchronization service")
        
        # Initial sync
        await self._sync_time()
        
        self._running = True
        self._sync_task = asyncio.create_task(self._sync_loop())
    
    async def stop_sync(self):
        """Stop the time synchronization service"""
        self._running = False
        
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Time synchronization service stopped")
    
    async def _sync_loop(self):
        """Background task to periodically sync time"""
        while self._running:
            try:
                await asyncio.sleep(self._sync_interval)
                
                if self._running:
                    await self._sync_time()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in time sync loop: {e}",
                                extra_data={"error": str(e)})
                await asyncio.sleep(30)  # Wait 30 seconds before retrying
    
    async def _sync_time(self):
        """Synchronize time with Binance servers"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # Record request time
                request_time = int(time.time() * 1000)
                
                async with session.get(self.server_time_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        server_time = int(data.get("serverTime", 0))
                        
                        # Record response time
                        response_time = int(time.time() * 1000)
                        
                        # Calculate network delay and adjust server time
                        network_delay = (response_time - request_time) // 2
                        adjusted_server_time = server_time + network_delay
                        
                        # Calculate offset
                        local_time = response_time
                        self._time_offset = adjusted_server_time - local_time
                        self._last_sync_time = time.time()
                        
                        self.logger.info(
                            f"Time synchronized - Offset: {self._time_offset}ms, Network delay: {network_delay * 2}ms",
                            extra_data={
                                "offset_ms": self._time_offset,
                                "network_delay_ms": network_delay * 2,
                                "server_time": server_time,
                                "local_time": local_time
                            }
                        )
                    else:
                        self.logger.error(f"Failed to get server time: HTTP {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Error syncing time: {e}",
                            extra_data={"error": str(e)})
    
    def get_server_time(self) -> int:
        """Get current server time in milliseconds"""
        if self._time_offset is None:
            self.logger.warning("Time not synchronized, using local time")
            return int(time.time() * 1000)
        
        local_time = int(time.time() * 1000)
        server_time = local_time + self._time_offset
        
        return server_time
    
    def get_server_datetime(self) -> datetime:
        """Get current server time as datetime object"""
        server_time_ms = self.get_server_time()
        return datetime.fromtimestamp(server_time_ms / 1000)
    
    def get_offset(self) -> Optional[int]:
        """Get current time offset in milliseconds"""
        return self._time_offset
    
    def is_synchronized(self) -> bool:
        """Check if time is synchronized"""
        return self._time_offset is not None
    
    def get_sync_age(self) -> Optional[float]:
        """Get age of last synchronization in seconds"""
        if not self._last_sync_time:
            return None
        
        return time.time() - self._last_sync_time
    
    def needs_sync(self) -> bool:
        """Check if synchronization is needed"""
        if not self.is_synchronized():
            return True
        
        sync_age = self.get_sync_age()
        if sync_age is None:
            return True
        
        # Sync if older than sync interval
        return sync_age > self._sync_interval
    
    def get_recv_window_adjusted_time(self, recv_window_ms: int = 5000) -> int:
        """Get server time adjusted for recv window"""
        server_time = self.get_server_time()
        
        # Subtract some buffer to ensure the request arrives within recv window
        buffer_ms = min(recv_window_ms // 4, 1000)  # 25% of recv window or 1 second, whichever is smaller
        
        return server_time - buffer_ms
    
    def validate_timestamp(self, timestamp: int, recv_window_ms: int = 5000) -> bool:
        """Validate if a timestamp is within acceptable recv window"""
        server_time = self.get_server_time()
        time_diff = abs(server_time - timestamp)
        
        return time_diff <= recv_window_ms
    
    def get_status(self) -> dict:
        """Get synchronization status"""
        sync_age = self.get_sync_age()
        
        return {
            "synchronized": self.is_synchronized(),
            "offset_ms": self._time_offset,
            "last_sync_age_seconds": sync_age,
            "needs_sync": self.needs_sync(),
            "running": self._running,
            "testnet": self.testnet,
            "current_server_time": self.get_server_time(),
            "current_local_time": int(time.time() * 1000)
        }