import asyncio
import aiohttp
import time
from typing import Optional, Dict, Any
from datetime import datetime

from binance_sdk_derivatives_trading_usds_futures.rest_api import DerivativesTradingUsdsFuturesRestAPI
from utils.logging import get_logger, TradingLoggerAdapter
from config.api_keys import APIKeyManager


class UserDataStreamManager:
    def __init__(self, api_key_manager: APIKeyManager, testnet: bool = True):
        self.api_key_manager = api_key_manager
        self.testnet = testnet
        self.logger: TradingLoggerAdapter = get_logger("user_data_stream")
        
        self.listen_key: Optional[str] = None
        self.listen_key_expires_at: Optional[float] = None
        self.keepalive_interval = 30 * 60  # 30 minutes (Binance requires < 60 min)
        self.rest_api = None
        
        self._keepalive_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self) -> bool:
        try:
            keys = self.api_key_manager.get_binance_keys("testnet" if self.testnet else "mainnet")
            
            self.rest_api = DerivativesTradingUsdsFuturesRestAPI(
                api_key=keys.api_key,
                api_secret=keys.api_secret,
                testnet=self.testnet
            )
            
            # Create initial listen key
            success = await self._create_listen_key()
            if success:
                self._running = True
                self._keepalive_task = asyncio.create_task(self._keepalive_loop())
                
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to initialize user data stream: {e}",
                            extra_data={"error": str(e)})
            return False
    
    async def _create_listen_key(self) -> bool:
        try:
            self.logger.info("Creating new listen key...")
            
            response = await self.rest_api.new_listen_key()
            
            if response and "listenKey" in response:
                self.listen_key = response["listenKey"]
                self.listen_key_expires_at = time.time() + 3600  # 1 hour from now
                
                self.logger.info("Listen key created successfully",
                               extra_data={"expires_at": datetime.fromtimestamp(self.listen_key_expires_at).isoformat()})
                return True
            else:
                self.logger.error("Failed to create listen key - invalid response",
                                extra_data={"response": response})
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating listen key: {e}",
                            extra_data={"error": str(e)})
            return False
    
    async def _extend_listen_key(self) -> bool:
        try:
            if not self.listen_key:
                self.logger.warning("No listen key to extend, creating new one")
                return await self._create_listen_key()
            
            self.logger.debug("Extending listen key...")
            
            response = await self.rest_api.keepalive_listen_key(listenKey=self.listen_key)
            
            # Binance returns empty response {} on success for keepalive
            if response is not None:
                self.listen_key_expires_at = time.time() + 3600  # Extend for another hour
                self.logger.debug("Listen key extended successfully",
                                extra_data={"expires_at": datetime.fromtimestamp(self.listen_key_expires_at).isoformat()})
                return True
            else:
                self.logger.error("Failed to extend listen key",
                                extra_data={"response": response})
                # Try to create a new listen key
                return await self._create_listen_key()
                
        except Exception as e:
            self.logger.error(f"Error extending listen key: {e}",
                            extra_data={"error": str(e)})
            # Try to create a new listen key on error
            return await self._create_listen_key()
    
    async def _delete_listen_key(self) -> bool:
        try:
            if not self.listen_key:
                return True
            
            self.logger.info("Deleting listen key...")
            
            response = await self.rest_api.close_listen_key(listenKey=self.listen_key)
            
            # Binance returns empty response {} on success for delete
            if response is not None:
                self.logger.info("Listen key deleted successfully")
                self.listen_key = None
                self.listen_key_expires_at = None
                return True
            else:
                self.logger.warning("Failed to delete listen key, but continuing",
                                  extra_data={"response": response})
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting listen key: {e}",
                            extra_data={"error": str(e)})
            return False
    
    async def _keepalive_loop(self):
        while self._running:
            try:
                # Sleep for keepalive interval (30 minutes)
                await asyncio.sleep(self.keepalive_interval)
                
                if not self._running:
                    break
                
                # Extend the listen key
                success = await self._extend_listen_key()
                if not success:
                    self.logger.error("Failed to maintain listen key, user data stream may be interrupted")
                
            except asyncio.CancelledError:
                self.logger.info("Keepalive task cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in keepalive loop: {e}",
                                extra_data={"error": str(e)})
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def shutdown(self):
        self._running = False
        
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
        
        # Clean up listen key
        await self._delete_listen_key()
        
        self.logger.info("User data stream manager shutdown complete")
    
    def get_listen_key(self) -> Optional[str]:
        return self.listen_key
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "has_listen_key": self.listen_key is not None,
            "expires_at": self.listen_key_expires_at,
            "expires_in_seconds": max(0, int(self.listen_key_expires_at - time.time())) if self.listen_key_expires_at else 0,
            "running": self._running,
            "testnet": self.testnet
        }
    
    def is_listen_key_valid(self) -> bool:
        if not self.listen_key or not self.listen_key_expires_at:
            return False
        
        # Consider key invalid if it expires in less than 5 minutes
        return (self.listen_key_expires_at - time.time()) > 300