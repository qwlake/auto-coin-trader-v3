from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
from datetime import datetime, timedelta

from utils.logging import get_logger, TradingLoggerAdapter
from utils.data_models import KlineData, MarkPriceData, OrderData, PositionData


class DataValidator:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.logger: TradingLoggerAdapter = get_logger(
            "data_validator", 
            {"symbol": self.symbol}
        )
        
        # Track data quality metrics
        self.stats = {
            "total_validated": 0,
            "validation_errors": 0,
            "kline_gaps": 0,
            "price_anomalies": 0,
            "volume_anomalies": 0,
            "last_validation": None
        }
        
        # Store last known values for gap detection
        self.last_kline_close_time: Optional[int] = None
        self.last_mark_price: Optional[Decimal] = None
        self.price_history: List[Decimal] = []
        self.max_price_history = 100
    
    def validate_kline(self, kline: KlineData) -> tuple[bool, List[str]]:
        """Validate kline data for consistency and anomalies"""
        errors = []
        self.stats["total_validated"] += 1
        
        try:
            # Basic data integrity checks
            if kline.symbol != self.symbol:
                errors.append(f"Symbol mismatch: expected {self.symbol}, got {kline.symbol}")
            
            if kline.open_time >= kline.close_time:
                errors.append(f"Invalid time range: open_time {kline.open_time} >= close_time {kline.close_time}")
            
            # Price validation
            if not self._validate_prices(kline):
                errors.append("Invalid price relationships")
            
            # Volume validation
            if not self._validate_volume(kline):
                errors.append("Invalid volume data")
            
            # Check for time gaps
            if self._check_time_gap(kline):
                errors.append("Time gap detected in kline sequence")
                self.stats["kline_gaps"] += 1
            
            # Check for price anomalies
            if self._check_price_anomaly(kline.close_price):
                errors.append("Price anomaly detected")
                self.stats["price_anomalies"] += 1
            
            # Update tracking data
            self.last_kline_close_time = kline.close_time
            self._update_price_history(kline.close_price)
            
            if errors:
                self.stats["validation_errors"] += 1
                self.logger.warning(
                    f"Kline validation failed: {', '.join(errors)}",
                    extra_data={
                        "kline_data": kline.to_dict(),
                        "errors": errors
                    }
                )
            
            self.stats["last_validation"] = datetime.utcnow().isoformat()
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"Error validating kline: {e}",
                            extra_data={"kline_data": kline.to_dict() if kline else None, "error": str(e)})
            return False, [f"Validation error: {str(e)}"]
    
    def validate_mark_price(self, mark_price: MarkPriceData) -> tuple[bool, List[str]]:
        """Validate mark price data"""
        errors = []
        self.stats["total_validated"] += 1
        
        try:
            # Basic data integrity checks
            if mark_price.symbol != self.symbol:
                errors.append(f"Symbol mismatch: expected {self.symbol}, got {mark_price.symbol}")
            
            # Price relationships
            if mark_price.mark_price <= 0:
                errors.append(f"Invalid mark price: {mark_price.mark_price}")
            
            if mark_price.index_price <= 0:
                errors.append(f"Invalid index price: {mark_price.index_price}")
            
            # Check mark price vs index price deviation (should be within reasonable range)
            if mark_price.mark_price > 0 and mark_price.index_price > 0:
                deviation = abs(mark_price.mark_price - mark_price.index_price) / mark_price.index_price
                if deviation > Decimal("0.1"):  # 10% deviation threshold
                    errors.append(f"Large mark price deviation from index: {deviation:.4f}")
            
            # Funding rate sanity check (typically between -0.75% to +0.75%)
            if abs(mark_price.funding_rate) > Decimal("0.0075"):
                errors.append(f"Unusual funding rate: {mark_price.funding_rate}")
            
            # Check for price anomalies
            if self._check_price_anomaly(mark_price.mark_price):
                errors.append("Mark price anomaly detected")
                self.stats["price_anomalies"] += 1
            
            # Update tracking data
            self.last_mark_price = mark_price.mark_price
            self._update_price_history(mark_price.mark_price)
            
            if errors:
                self.stats["validation_errors"] += 1
                self.logger.warning(
                    f"Mark price validation failed: {', '.join(errors)}",
                    extra_data={
                        "mark_price_data": mark_price.to_dict(),
                        "errors": errors
                    }
                )
            
            self.stats["last_validation"] = datetime.utcnow().isoformat()
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"Error validating mark price: {e}",
                            extra_data={"mark_price_data": mark_price.to_dict() if mark_price else None, "error": str(e)})
            return False, [f"Validation error: {str(e)}"]
    
    def validate_order(self, order: OrderData) -> tuple[bool, List[str]]:
        """Validate order data"""
        errors = []
        self.stats["total_validated"] += 1
        
        try:
            # Basic data integrity
            if order.symbol != self.symbol:
                errors.append(f"Symbol mismatch: expected {self.symbol}, got {order.symbol}")
            
            if order.original_quantity <= 0:
                errors.append(f"Invalid quantity: {order.original_quantity}")
            
            # Price validation for limit orders
            if order.price is not None and order.price <= 0:
                errors.append(f"Invalid price: {order.price}")
            
            # Quantity relationships
            if order.cumulative_filled_quantity > order.original_quantity:
                errors.append(f"Filled quantity ({order.cumulative_filled_quantity}) > original quantity ({order.original_quantity})")
            
            if order.cumulative_filled_quantity < 0:
                errors.append(f"Negative filled quantity: {order.cumulative_filled_quantity}")
            
            # Status validation
            if order.order_status == "FILLED" and order.cumulative_filled_quantity != order.original_quantity:
                errors.append(f"Order marked as FILLED but quantities don't match: {order.cumulative_filled_quantity} != {order.original_quantity}")
            
            if errors:
                self.stats["validation_errors"] += 1
                self.logger.warning(
                    f"Order validation failed: {', '.join(errors)}",
                    extra_data={
                        "order_data": order.to_dict(),
                        "errors": errors
                    }
                )
            
            self.stats["last_validation"] = datetime.utcnow().isoformat()
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"Error validating order: {e}",
                            extra_data={"order_data": order.to_dict() if order else None, "error": str(e)})
            return False, [f"Validation error: {str(e)}"]
    
    def _validate_prices(self, kline: KlineData) -> bool:
        """Validate price relationships in kline data"""
        try:
            # All prices should be positive
            if any(price <= 0 for price in [kline.open_price, kline.high_price, kline.low_price, kline.close_price]):
                return False
            
            # High should be >= all other prices
            if (kline.high_price < kline.open_price or 
                kline.high_price < kline.close_price or 
                kline.high_price < kline.low_price):
                return False
            
            # Low should be <= all other prices
            if (kline.low_price > kline.open_price or 
                kline.low_price > kline.close_price or 
                kline.low_price > kline.high_price):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_volume(self, kline: KlineData) -> bool:
        """Validate volume data"""
        try:
            # Volumes should be non-negative
            if kline.volume < 0 or kline.quote_volume < 0:
                return False
            
            # Base and quote volumes should have reasonable relationship
            if kline.volume > 0 and kline.quote_volume > 0:
                avg_price = kline.quote_volume / kline.volume
                # Average price should be within OHLC range
                if avg_price < kline.low_price or avg_price > kline.high_price:
                    self.logger.debug(f"Average price {avg_price} outside OHLC range [{kline.low_price}, {kline.high_price}]")
                    self.stats["volume_anomalies"] += 1
            
            return True
            
        except Exception:
            return False
    
    def _check_time_gap(self, kline: KlineData) -> bool:
        """Check for time gaps in kline sequence"""
        if self.last_kline_close_time is None:
            return False
        
        # For 1-minute klines, expect 60 seconds between close times
        expected_interval_ms = 60 * 1000
        actual_gap = kline.open_time - self.last_kline_close_time
        
        # Allow some tolerance for timing variations
        tolerance_ms = 5000  # 5 seconds
        
        return abs(actual_gap - expected_interval_ms) > tolerance_ms
    
    def _check_price_anomaly(self, current_price: Decimal) -> bool:
        """Check for price anomalies based on recent price history"""
        if len(self.price_history) < 10:  # Need sufficient history
            return False
        
        try:
            # Calculate recent average and standard deviation
            recent_prices = self.price_history[-20:]  # Last 20 prices
            avg_price = sum(recent_prices) / len(recent_prices)
            
            # Simple standard deviation calculation
            variance = sum((price - avg_price) ** 2 for price in recent_prices) / len(recent_prices)
            std_dev = variance ** Decimal("0.5")
            
            # Flag as anomaly if price is more than 5 standard deviations from mean
            deviation = abs(current_price - avg_price)
            
            return deviation > (std_dev * 5)
            
        except Exception:
            return False
    
    def _update_price_history(self, price: Decimal):
        """Update price history for anomaly detection"""
        self.price_history.append(price)
        
        # Keep only recent history
        if len(self.price_history) > self.max_price_history:
            self.price_history = self.price_history[-self.max_price_history:]
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        stats = self.stats.copy()
        
        if stats["total_validated"] > 0:
            stats["error_rate"] = stats["validation_errors"] / stats["total_validated"]
            stats["gap_rate"] = stats["kline_gaps"] / stats["total_validated"]
            stats["anomaly_rate"] = stats["price_anomalies"] / stats["total_validated"]
        else:
            stats["error_rate"] = 0.0
            stats["gap_rate"] = 0.0
            stats["anomaly_rate"] = 0.0
        
        stats["price_history_size"] = len(self.price_history)
        stats["last_price"] = float(self.price_history[-1]) if self.price_history else None
        
        return stats
    
    def reset_stats(self):
        """Reset validation statistics"""
        self.stats = {
            "total_validated": 0,
            "validation_errors": 0,
            "kline_gaps": 0,
            "price_anomalies": 0,
            "last_validation": None
        }
        
        self.logger.info("Validation statistics reset")


class MultiSymbolDataValidator:
    def __init__(self, symbols: List[str]):
        self.symbols = [symbol.upper() for symbol in symbols]
        self.validators: Dict[str, DataValidator] = {}
        self.logger: TradingLoggerAdapter = get_logger("multi_symbol_validator")
        
        # Initialize validators for each symbol
        for symbol in self.symbols:
            self.validators[symbol] = DataValidator(symbol)
        
        self.logger.info(f"Initialized multi-symbol validator for {len(self.symbols)} symbols")
    
    def validate_kline(self, symbol: str, kline: KlineData) -> tuple[bool, List[str]]:
        """Validate kline data for a specific symbol"""
        symbol = symbol.upper()
        if symbol not in self.validators:
            return False, [f"No validator configured for symbol {symbol}"]
        
        return self.validators[symbol].validate_kline(kline)
    
    def validate_mark_price(self, symbol: str, mark_price: MarkPriceData) -> tuple[bool, List[str]]:
        """Validate mark price data for a specific symbol"""
        symbol = symbol.upper()
        if symbol not in self.validators:
            return False, [f"No validator configured for symbol {symbol}"]
        
        return self.validators[symbol].validate_mark_price(mark_price)
    
    def validate_order(self, symbol: str, order: OrderData) -> tuple[bool, List[str]]:
        """Validate order data for a specific symbol"""
        symbol = symbol.upper()
        if symbol not in self.validators:
            return False, [f"No validator configured for symbol {symbol}"]
        
        return self.validators[symbol].validate_order(order)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get validation statistics for all symbols"""
        return {symbol: validator.get_validation_stats() 
                for symbol, validator in self.validators.items()}
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics across all symbols"""
        all_stats = self.get_all_stats()
        
        if not all_stats:
            return {}
        
        total_validated = sum(stats["total_validated"] for stats in all_stats.values())
        total_errors = sum(stats["validation_errors"] for stats in all_stats.values())
        total_gaps = sum(stats["kline_gaps"] for stats in all_stats.values())
        total_anomalies = sum(stats["price_anomalies"] for stats in all_stats.values())
        
        return {
            "total_symbols": len(self.symbols),
            "total_validated": total_validated,
            "total_errors": total_errors,
            "total_gaps": total_gaps,
            "total_anomalies": total_anomalies,
            "overall_error_rate": total_errors / total_validated if total_validated > 0 else 0.0,
            "symbols": list(self.symbols)
        }