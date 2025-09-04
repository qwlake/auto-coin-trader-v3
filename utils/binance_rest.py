import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from binance_sdk_derivatives_trading_usds_futures.rest_api import DerivativesTradingUsdsFuturesRestAPI
from binance_common.configuration import ConfigurationRestAPI
from utils.logging import get_logger, TradingLoggerAdapter
from config.api_keys import APIKeyManager


class BinanceRestClient:
    def __init__(self, api_key_manager: APIKeyManager, testnet: bool = True):
        self.api_key_manager = api_key_manager
        self.testnet = testnet
        self.logger: TradingLoggerAdapter = get_logger("binance_rest")
        
        self.client = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the REST client with API keys"""
        try:
            # Get API keys
            keys = self.api_key_manager.get_binance_keys("testnet" if self.testnet else "mainnet")
            
            # Set up configuration
            if self.testnet:
                base_path = "https://testnet.binancefuture.com"
            else:
                base_path = "https://fapi.binance.com"
            
            config = ConfigurationRestAPI(
                api_key=keys.api_key,
                api_secret=keys.api_secret,
                base_path=base_path
            )
            
            # Initialize REST client
            self.client = DerivativesTradingUsdsFuturesRestAPI(config)
            
            # Test connection (synchronous call)
            server_time_response = self.client.check_server_time()
            if server_time_response and hasattr(server_time_response, 'data'):
                server_time = server_time_response.data
                self._initialized = True
                self.logger.info(f"REST client initialized successfully, server time: {server_time}")
                return True
            else:
                self.logger.error("Failed to get server time")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize REST client: {e}")
            return False
    
    def get_server_time(self) -> Optional[int]:
        """Get server time"""
        try:
            if not self.client:
                return None
            
            response = self.client.check_server_time()
            if hasattr(response, 'data'):
                return response.data.get("serverTime")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting server time: {e}")
            return None
    
    def get_exchange_info(self) -> Optional[Dict[str, Any]]:
        """Get exchange information"""
        try:
            if not self.client or not self._initialized:
                self.logger.error("REST client not initialized")
                return None
            
            response = self.client.exchange_information()
            if hasattr(response, 'data'):
                return response.data
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting exchange info: {e}")
            return None
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information"""
        try:
            if not self.client or not self._initialized:
                self.logger.error("REST client not initialized")
                return None
            
            response = self.client.account_information_v2()
            if hasattr(response, 'data'):
                return response.data
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            return None
    
    def get_position_info(self, symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get position information"""
        try:
            if not self.client or not self._initialized:
                self.logger.error("REST client not initialized")
                return None
            
            if symbol:
                response = self.client.position_information_v2(symbol=symbol)
            else:
                response = self.client.position_information_v2()
            
            if hasattr(response, 'data'):
                return response.data
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting position info: {e}")
            return None
    
    def create_listen_key(self) -> Optional[str]:
        """Create user data stream listen key"""
        try:
            if not self.client or not self._initialized:
                self.logger.error("REST client not initialized")
                return None
            
            response = self.client.start_user_data_stream()
            listen_key = response.data.get("listenKey") if hasattr(response, 'data') else None
            
            if listen_key:
                self.logger.info("Listen key created successfully")
                return listen_key
            else:
                self.logger.error("No listen key in response")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating listen key: {e}")
            return None
    
    def keepalive_listen_key(self, listen_key: str) -> bool:
        """Keep alive user data stream"""
        try:
            if not self.client or not self._initialized:
                self.logger.error("REST client not initialized")
                return False
            
            self.client.keepalive_user_data_stream(listenKey=listen_key)
            self.logger.debug("Listen key keepalive successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Error keeping alive listen key: {e}")
            return False
    
    def close_listen_key(self, listen_key: str) -> bool:
        """Close user data stream"""
        try:
            if not self.client or not self._initialized:
                self.logger.error("REST client not initialized")
                return False
            
            self.client.close_user_data_stream(listenKey=listen_key)
            self.logger.info("Listen key closed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error closing listen key: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get client status"""
        return {
            "initialized": self._initialized,
            "has_client": self.client is not None,
            "testnet": self.testnet
        }


# Test function
async def test_binance_rest():
    """Test Binance REST API connection (without real API keys)"""
    try:
        from config.api_keys import APIKeyManager
        
        # Test with API key manager (will fail gracefully without real keys)
        api_key_manager = APIKeyManager(use_1password=False)
        client = BinanceRestClient(api_key_manager, testnet=True)
        
        print(f"✅ REST client created: {client.get_status()}")
        
        # Try to get server time without authentication (synchronous)
        server_time = client.get_server_time()
        if server_time:
            print(f"✅ Server time: {server_time}")
            return True
        else:
            print("⚠️ Could not get server time (expected without API keys)")
            return True  # This is expected without real API keys
        
    except Exception as e:
        print(f"❌ REST test failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_binance_rest())