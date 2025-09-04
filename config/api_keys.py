from typing import Optional
import os
import subprocess
import json
from pydantic import BaseModel


class APIKeys(BaseModel):
    api_key: str
    api_secret: str


class APIKeyManager:
    def __init__(self, use_1password: bool = True):
        self.use_1password = use_1password
    
    def get_binance_keys(self, mode: str = "testnet") -> APIKeys:
        if self.use_1password and self._is_1password_available():
            return self._get_keys_from_1password(mode)
        else:
            return self._get_keys_from_env()
    
    def _is_1password_available(self) -> bool:
        try:
            result = subprocess.run(['op', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _get_keys_from_1password(self, mode: str) -> APIKeys:
        try:
            vault_item = f"Binance-{mode.capitalize()}"
            
            api_key_cmd = ['op', 'item', 'get', vault_item, '--field', 'api_key']
            api_secret_cmd = ['op', 'item', 'get', vault_item, '--field', 'api_secret']
            
            api_key_result = subprocess.run(api_key_cmd, capture_output=True, text=True, timeout=10)
            api_secret_result = subprocess.run(api_secret_cmd, capture_output=True, text=True, timeout=10)
            
            if api_key_result.returncode != 0 or api_secret_result.returncode != 0:
                raise Exception(f"Failed to retrieve keys from 1Password: {api_key_result.stderr or api_secret_result.stderr}")
            
            return APIKeys(
                api_key=api_key_result.stdout.strip(),
                api_secret=api_secret_result.stdout.strip()
            )
        
        except Exception as e:
            print(f"Warning: Failed to get keys from 1Password: {e}")
            print("Falling back to environment variables...")
            return self._get_keys_from_env()
    
    def _get_keys_from_env(self) -> APIKeys:
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        
        if not api_key or not api_secret:
            raise ValueError(
                "Binance API credentials not found. "
                "Please set BINANCE_API_KEY and BINANCE_API_SECRET environment variables, "
                "or configure 1Password with Binance credentials."
            )
        
        return APIKeys(api_key=api_key, api_secret=api_secret)