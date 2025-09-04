import json
import asyncio
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from decimal import Decimal

from utils.logging import get_logger, TradingLoggerAdapter


class KlineStreamHandler:
    def __init__(self, symbol: str, interval: str, callback: Optional[Callable] = None):
        self.symbol = symbol.upper()
        self.interval = interval
        self.callback = callback
        self.logger: TradingLoggerAdapter = get_logger(
            "kline_handler", 
            {"symbol": symbol, "interval": interval}
        )
        
        self.last_kline = None
        self.kline_count = 0
    
    async def handle_kline_data(self, data: Dict[str, Any]):
        try:
            if data.get("e") != "kline":
                self.logger.warning("Received non-kline data", extra_data={"data": data})
                return
            
            kline_data = data.get("k", {})
            if not kline_data:
                self.logger.warning("No kline data in message", extra_data={"data": data})
                return
            
            # Parse kline data
            parsed_kline = {
                "symbol": kline_data.get("s"),
                "open_time": int(kline_data.get("t")),
                "close_time": int(kline_data.get("T")),
                "open_price": Decimal(str(kline_data.get("o", "0"))),
                "high_price": Decimal(str(kline_data.get("h", "0"))),
                "low_price": Decimal(str(kline_data.get("l", "0"))),
                "close_price": Decimal(str(kline_data.get("c", "0"))),
                "volume": Decimal(str(kline_data.get("v", "0"))),
                "quote_volume": Decimal(str(kline_data.get("q", "0"))),
                "trades_count": int(kline_data.get("n", 0)),
                "is_closed": bool(kline_data.get("x", False)),
                "interval": kline_data.get("i"),
                "first_trade_id": int(kline_data.get("f", 0)),
                "last_trade_id": int(kline_data.get("L", 0)),
                "base_asset_volume": Decimal(str(kline_data.get("V", "0"))),
                "quote_asset_volume": Decimal(str(kline_data.get("Q", "0")))
            }
            
            self.last_kline = parsed_kline
            self.kline_count += 1
            
            # Log only closed klines to reduce noise
            if parsed_kline["is_closed"]:
                self.logger.info(
                    f"Closed kline: {parsed_kline['close_price']} (Vol: {parsed_kline['volume']})",
                    extra_data={
                        "kline_data": {
                            "open": float(parsed_kline["open_price"]),
                            "high": float(parsed_kline["high_price"]),
                            "low": float(parsed_kline["low_price"]),
                            "close": float(parsed_kline["close_price"]),
                            "volume": float(parsed_kline["volume"]),
                            "trades": parsed_kline["trades_count"]
                        }
                    }
                )
            
            # Call custom callback if provided
            if self.callback:
                await self._safe_callback(parsed_kline)
                
        except Exception as e:
            self.logger.error(f"Error handling kline data: {e}", 
                            extra_data={"data": data, "error": str(e)})
    
    async def _safe_callback(self, kline_data: Dict[str, Any]):
        try:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(kline_data)
            else:
                self.callback(kline_data)
        except Exception as e:
            self.logger.error(f"Error in kline callback: {e}",
                            extra_data={"kline_data": kline_data, "error": str(e)})
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "total_klines_received": self.kline_count,
            "last_kline_time": self.last_kline.get("close_time") if self.last_kline else None,
            "last_price": float(self.last_kline.get("close_price", 0)) if self.last_kline else None
        }


class MarkPriceStreamHandler:
    def __init__(self, symbol: str, callback: Optional[Callable] = None):
        self.symbol = symbol.upper()
        self.callback = callback
        self.logger: TradingLoggerAdapter = get_logger(
            "markprice_handler", 
            {"symbol": symbol}
        )
        
        self.last_mark_price = None
        self.price_updates_count = 0
    
    async def handle_mark_price_data(self, data: Dict[str, Any]):
        try:
            if data.get("e") != "markPriceUpdate":
                self.logger.warning("Received non-mark price data", extra_data={"data": data})
                return
            
            # Parse mark price data
            parsed_data = {
                "symbol": data.get("s"),
                "mark_price": Decimal(str(data.get("p", "0"))),
                "index_price": Decimal(str(data.get("i", "0"))),
                "estimated_settle_price": Decimal(str(data.get("P", "0"))),
                "funding_rate": Decimal(str(data.get("r", "0"))),
                "next_funding_time": int(data.get("T", 0)),
                "event_time": int(data.get("E", 0))
            }
            
            self.last_mark_price = parsed_data
            self.price_updates_count += 1
            
            # Log periodically to avoid spam (every 100 updates)
            if self.price_updates_count % 100 == 0:
                self.logger.info(
                    f"Mark price update: {parsed_data['mark_price']} (Funding: {parsed_data['funding_rate']})",
                    extra_data={
                        "mark_price_data": {
                            "mark_price": float(parsed_data["mark_price"]),
                            "index_price": float(parsed_data["index_price"]),
                            "funding_rate": float(parsed_data["funding_rate"]),
                            "next_funding_time": parsed_data["next_funding_time"]
                        }
                    }
                )
            
            # Call custom callback if provided
            if self.callback:
                await self._safe_callback(parsed_data)
                
        except Exception as e:
            self.logger.error(f"Error handling mark price data: {e}", 
                            extra_data={"data": data, "error": str(e)})
    
    async def _safe_callback(self, price_data: Dict[str, Any]):
        try:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(price_data)
            else:
                self.callback(price_data)
        except Exception as e:
            self.logger.error(f"Error in mark price callback: {e}",
                            extra_data={"price_data": price_data, "error": str(e)})
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "total_updates_received": self.price_updates_count,
            "last_update_time": self.last_mark_price.get("event_time") if self.last_mark_price else None,
            "last_mark_price": float(self.last_mark_price.get("mark_price", 0)) if self.last_mark_price else None,
            "last_funding_rate": float(self.last_mark_price.get("funding_rate", 0)) if self.last_mark_price else None
        }


class UserDataStreamHandler:
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.logger: TradingLoggerAdapter = get_logger("userdata_handler")
        
        self.account_updates_count = 0
        self.order_updates_count = 0
        self.last_account_update = None
        self.last_order_update = None
    
    async def handle_user_data(self, data: Dict[str, Any]):
        try:
            event_type = data.get("e")
            
            if event_type == "ACCOUNT_UPDATE":
                await self._handle_account_update(data)
            elif event_type == "ORDER_TRADE_UPDATE":
                await self._handle_order_update(data)
            elif event_type == "listenKeyExpired":
                self.logger.warning("Listen key expired, need to refresh")
            else:
                self.logger.debug(f"Unknown user data event: {event_type}", extra_data={"data": data})
            
            # Call custom callback if provided
            if self.callback:
                await self._safe_callback(data)
                
        except Exception as e:
            self.logger.error(f"Error handling user data: {e}", 
                            extra_data={"data": data, "error": str(e)})
    
    async def _handle_account_update(self, data: Dict[str, Any]):
        self.account_updates_count += 1
        self.last_account_update = data
        
        account_data = data.get("a", {})
        balances = account_data.get("B", [])
        positions = account_data.get("P", [])
        
        self.logger.info(
            f"Account update: {len(balances)} balances, {len(positions)} positions",
            extra_data={
                "account_update": {
                    "event_time": data.get("E"),
                    "transaction_time": data.get("T"),
                    "balances_count": len(balances),
                    "positions_count": len(positions)
                }
            }
        )
    
    async def _handle_order_update(self, data: Dict[str, Any]):
        self.order_updates_count += 1
        self.last_order_update = data
        
        order_data = data.get("o", {})
        symbol = order_data.get("s")
        side = order_data.get("S")
        order_type = order_data.get("ot")
        order_status = order_data.get("X")
        quantity = order_data.get("q")
        price = order_data.get("p")
        
        self.logger.info(
            f"Order update: {symbol} {side} {order_type} - {order_status}",
            extra_data={
                "order_update": {
                    "symbol": symbol,
                    "side": side,
                    "order_type": order_type,
                    "status": order_status,
                    "quantity": quantity,
                    "price": price,
                    "event_time": data.get("E"),
                    "transaction_time": data.get("T")
                }
            }
        )
    
    async def _safe_callback(self, user_data: Dict[str, Any]):
        try:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(user_data)
            else:
                self.callback(user_data)
        except Exception as e:
            self.logger.error(f"Error in user data callback: {e}",
                            extra_data={"user_data": user_data, "error": str(e)})
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "account_updates_received": self.account_updates_count,
            "order_updates_received": self.order_updates_count,
            "last_account_update_time": self.last_account_update.get("E") if self.last_account_update else None,
            "last_order_update_time": self.last_order_update.get("E") if self.last_order_update else None
        }