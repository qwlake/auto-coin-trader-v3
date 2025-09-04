import json
from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from datetime import datetime, timedelta

from utils.logging import get_logger, TradingLoggerAdapter


class ExchangeInfo:
    def __init__(self):
        self.logger: TradingLoggerAdapter = get_logger("exchange_info")
        self.exchange_info: Dict[str, Any] = {}
        self.symbol_filters: Dict[str, Dict[str, Any]] = {}
        self.last_updated: Optional[datetime] = None
        self.update_interval = timedelta(hours=1)  # Update every hour
    
    def update_exchange_info(self, exchange_info_data: Dict[str, Any]):
        try:
            self.exchange_info = exchange_info_data
            self.last_updated = datetime.utcnow()
            
            # Parse symbol filters for quick access
            self.symbol_filters = {}
            
            for symbol_data in exchange_info_data.get("symbols", []):
                symbol = symbol_data.get("symbol")
                if not symbol:
                    continue
                
                filters = {}
                for filter_data in symbol_data.get("filters", []):
                    filter_type = filter_data.get("filterType")
                    if filter_type:
                        filters[filter_type] = filter_data
                
                self.symbol_filters[symbol] = {
                    "filters": filters,
                    "base_asset": symbol_data.get("baseAsset"),
                    "quote_asset": symbol_data.get("quoteAsset"),
                    "status": symbol_data.get("status"),
                    "base_asset_precision": symbol_data.get("baseAssetPrecision", 8),
                    "quote_precision": symbol_data.get("quotePrecision", 8),
                    "price_precision": symbol_data.get("pricePrecision", 8),
                    "quantity_precision": symbol_data.get("quantityPrecision", 8)
                }
            
            self.logger.info(f"Updated exchange info for {len(self.symbol_filters)} symbols")
            
        except Exception as e:
            self.logger.error(f"Error updating exchange info: {e}",
                            extra_data={"error": str(e)})
    
    def needs_update(self) -> bool:
        if not self.last_updated:
            return True
        return datetime.utcnow() - self.last_updated > self.update_interval
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self.symbol_filters.get(symbol.upper())
    
    def get_filter(self, symbol: str, filter_type: str) -> Optional[Dict[str, Any]]:
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return None
        
        return symbol_info["filters"].get(filter_type)


class PrecisionManager:
    def __init__(self, exchange_info: ExchangeInfo):
        self.exchange_info = exchange_info
        self.logger: TradingLoggerAdapter = get_logger("precision_manager")
    
    def round_quantity(self, symbol: str, quantity: Decimal) -> Decimal:
        lot_size_filter = self.exchange_info.get_filter(symbol, "LOT_SIZE")
        if not lot_size_filter:
            self.logger.warning(f"No LOT_SIZE filter for {symbol}, using default precision")
            return quantity.quantize(Decimal("0.00001"))
        
        step_size = Decimal(str(lot_size_filter.get("stepSize", "0.00001")))
        
        # Round down to nearest step size
        steps = quantity / step_size
        rounded_steps = steps.quantize(Decimal("1"), rounding=ROUND_DOWN)
        rounded_quantity = rounded_steps * step_size
        
        return rounded_quantity
    
    def round_price(self, symbol: str, price: Decimal) -> Decimal:
        price_filter = self.exchange_info.get_filter(symbol, "PRICE_FILTER")
        if not price_filter:
            self.logger.warning(f"No PRICE_FILTER for {symbol}, using default precision")
            return price.quantize(Decimal("0.01"))
        
        tick_size = Decimal(str(price_filter.get("tickSize", "0.01")))
        
        # Round to nearest tick size
        ticks = price / tick_size
        rounded_ticks = ticks.quantize(Decimal("1"), rounding=ROUND_DOWN)
        rounded_price = rounded_ticks * tick_size
        
        return rounded_price
    
    def validate_quantity(self, symbol: str, quantity: Decimal) -> tuple[bool, str]:
        lot_size_filter = self.exchange_info.get_filter(symbol, "LOT_SIZE")
        if not lot_size_filter:
            return False, f"No LOT_SIZE filter available for {symbol}"
        
        min_qty = Decimal(str(lot_size_filter.get("minQty", "0")))
        max_qty = Decimal(str(lot_size_filter.get("maxQty", "9999999999")))
        step_size = Decimal(str(lot_size_filter.get("stepSize", "0.00001")))
        
        if quantity < min_qty:
            return False, f"Quantity {quantity} below minimum {min_qty}"
        
        if quantity > max_qty:
            return False, f"Quantity {quantity} above maximum {max_qty}"
        
        # Check if quantity is valid step size
        remainder = (quantity - min_qty) % step_size
        if remainder != 0:
            return False, f"Quantity {quantity} not valid step size (stepSize: {step_size})"
        
        return True, "Valid quantity"
    
    def validate_price(self, symbol: str, price: Decimal) -> tuple[bool, str]:
        price_filter = self.exchange_info.get_filter(symbol, "PRICE_FILTER")
        if not price_filter:
            return False, f"No PRICE_FILTER available for {symbol}"
        
        min_price = Decimal(str(price_filter.get("minPrice", "0")))
        max_price = Decimal(str(price_filter.get("maxPrice", "9999999999")))
        tick_size = Decimal(str(price_filter.get("tickSize", "0.01")))
        
        if price < min_price:
            return False, f"Price {price} below minimum {min_price}"
        
        if price > max_price:
            return False, f"Price {price} above maximum {max_price}"
        
        # Check if price is valid tick size
        remainder = (price - min_price) % tick_size
        if remainder != 0:
            return False, f"Price {price} not valid tick size (tickSize: {tick_size})"
        
        return True, "Valid price"
    
    def validate_notional(self, symbol: str, price: Decimal, quantity: Decimal) -> tuple[bool, str]:
        notional_filter = self.exchange_info.get_filter(symbol, "MIN_NOTIONAL")
        if not notional_filter:
            self.logger.debug(f"No MIN_NOTIONAL filter for {symbol}")
            return True, "No notional validation required"
        
        min_notional = Decimal(str(notional_filter.get("minNotional", "0")))
        notional_value = price * quantity
        
        if notional_value < min_notional:
            return False, f"Notional {notional_value} below minimum {min_notional}"
        
        return True, "Valid notional"
    
    def validate_order(self, symbol: str, side: str, order_type: str, 
                      quantity: Decimal, price: Optional[Decimal] = None) -> tuple[bool, str]:
        # Validate quantity
        qty_valid, qty_msg = self.validate_quantity(symbol, quantity)
        if not qty_valid:
            return False, qty_msg
        
        # Validate price (for limit orders)
        if price is not None:
            price_valid, price_msg = self.validate_price(symbol, price)
            if not price_valid:
                return False, price_msg
            
            # Validate notional
            notional_valid, notional_msg = self.validate_notional(symbol, price, quantity)
            if not notional_valid:
                return False, notional_msg
        
        return True, "Order validation passed"
    
    def get_symbol_precision(self, symbol: str) -> Dict[str, int]:
        symbol_info = self.exchange_info.get_symbol_info(symbol)
        if not symbol_info:
            return {
                "price_precision": 8,
                "quantity_precision": 8,
                "base_asset_precision": 8,
                "quote_precision": 8
            }
        
        return {
            "price_precision": symbol_info.get("price_precision", 8),
            "quantity_precision": symbol_info.get("quantity_precision", 8),
            "base_asset_precision": symbol_info.get("base_asset_precision", 8),
            "quote_precision": symbol_info.get("quote_precision", 8)
        }
    
    def format_quantity(self, symbol: str, quantity: Decimal) -> str:
        precision = self.get_symbol_precision(symbol)
        return f"{quantity:.{precision['quantity_precision']}f}".rstrip('0').rstrip('.')
    
    def format_price(self, symbol: str, price: Decimal) -> str:
        precision = self.get_symbol_precision(symbol)
        return f"{price:.{precision['price_precision']}f}".rstrip('0').rstrip('.')
    
    def calculate_position_size(self, symbol: str, usd_amount: Decimal, 
                               entry_price: Decimal) -> Decimal:
        # Calculate base quantity from USD amount
        base_quantity = usd_amount / entry_price
        
        # Round to valid lot size
        rounded_quantity = self.round_quantity(symbol, base_quantity)
        
        return rounded_quantity
    
    def get_min_order_size(self, symbol: str, current_price: Optional[Decimal] = None) -> Dict[str, Decimal]:
        lot_size_filter = self.exchange_info.get_filter(symbol, "LOT_SIZE")
        notional_filter = self.exchange_info.get_filter(symbol, "MIN_NOTIONAL")
        
        min_qty = Decimal("0")
        min_notional = Decimal("0")
        
        if lot_size_filter:
            min_qty = Decimal(str(lot_size_filter.get("minQty", "0")))
        
        if notional_filter:
            min_notional = Decimal(str(notional_filter.get("minNotional", "0")))
        
        result = {
            "min_quantity": min_qty,
            "min_notional": min_notional
        }
        
        # Calculate minimum quantity required to meet notional requirement
        if current_price and min_notional > 0:
            min_qty_for_notional = min_notional / current_price
            result["min_quantity_for_notional"] = self.round_quantity(symbol, min_qty_for_notional)
        
        return result