from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, UTC
from decimal import Decimal
from enum import Enum

from utils.data_models import KlineData, MarkPriceData
from utils.logging import get_logger, TradingLoggerAdapter
from database.models import SignalType


class StrategyState(str, Enum):
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class StrategySignal:
    """Strategy signal data structure"""
    def __init__(
        self,
        symbol: str,
        signal_type: SignalType,
        price: Decimal,
        quantity: Optional[Decimal] = None,
        confidence: Optional[Decimal] = None,
        valid_until: Optional[datetime] = None,
        market_conditions: Optional[Dict[str, Any]] = None,
        indicators: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ):
        self.symbol = symbol
        self.signal_type = signal_type
        self.price = price
        self.quantity = quantity
        self.confidence = confidence
        self.valid_until = valid_until
        self.market_conditions = market_conditions or {}
        self.indicators = indicators or {}
        self.notes = notes
        self.created_at = datetime.now(UTC)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary for database storage"""
        return {
            "strategy": self.__class__.__name__,
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "price": self.price,
            "quantity": self.quantity,
            "confidence": self.confidence,
            "valid_until": self.valid_until,
            "market_conditions": self.market_conditions,
            "indicators": self.indicators,
            "notes": self.notes
        }


class BaseStrategy(ABC):
    """Base class for all trading strategies"""

    @classmethod
    @abstractmethod
    def get_strategy_name(cls) -> str:
        """Return strategy name"""
        pass

    def __init__(self, symbol: str, config: Dict[str, Any]):
        self.strategy_name = self.get_strategy_name()
        self.symbol = symbol
        self.config = config
        self.state = StrategyState.INACTIVE
        self.logger: TradingLoggerAdapter = get_logger(
            f"strategy.{self.__class__.__name__}.{symbol}",
            {"strategy": self.__class__.__name__, "symbol": symbol}
        )
        
        # Strategy metrics
        self.signals_generated = 0
        self.last_signal_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        
        # Data buffers
        self.klines: List[KlineData] = []
        self.mark_prices: List[MarkPriceData] = []
        
        # Configuration validation
        self._validate_config()
        
        self.logger.info(f"Initialized strategy: {self.__class__.__name__} for {symbol}")
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate strategy configuration"""
        pass
    
    @abstractmethod
    def process_kline(self, kline: KlineData) -> List[StrategySignal]:
        """
        Process new kline data and generate signals
        
        Args:
            kline: New kline data
            
        Returns:
            List of generated signals (can be empty)
        """
        pass
    
    @abstractmethod
    def process_mark_price(self, mark_price: MarkPriceData) -> List[StrategySignal]:
        """
        Process new mark price data and generate signals
        
        Args:
            mark_price: New mark price data
            
        Returns:
            List of generated signals (can be empty)
        """
        pass
    
    @abstractmethod
    def get_required_data_length(self) -> int:
        """
        Return the minimum number of klines required for the strategy to work
        
        Returns:
            Minimum number of klines needed
        """
        pass

    
    def start(self) -> bool:
        """Start the strategy"""
        try:
            if self.state == StrategyState.ACTIVE:
                self.logger.warning("Strategy already active")
                return True
                
            self.state = StrategyState.ACTIVE
            self.logger.info("Strategy started")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start strategy: {e}")
            self.state = StrategyState.ERROR
            self.last_error = str(e)
            return False
    
    def pause(self) -> bool:
        """Pause the strategy"""
        try:
            if self.state != StrategyState.ACTIVE:
                self.logger.warning(f"Cannot pause strategy in state: {self.state}")
                return False
                
            self.state = StrategyState.PAUSED
            self.logger.info("Strategy paused")
            return True
        except Exception as e:
            self.logger.error(f"Failed to pause strategy: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the strategy"""
        try:
            self.state = StrategyState.INACTIVE
            self.logger.info("Strategy stopped")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop strategy: {e}")
            self.state = StrategyState.ERROR
            self.last_error = str(e)
            return False
    
    def is_ready(self) -> bool:
        """Check if strategy has enough data to generate signals"""
        return (
            self.state == StrategyState.ACTIVE and
            len(self.klines) >= self.get_required_data_length()
        )
    
    def add_kline(self, kline: KlineData) -> List[StrategySignal]:
        """
        Add new kline data and process it
        
        Args:
            kline: New kline data
            
        Returns:
            List of generated signals
        """
        try:
            # Add to buffer
            self.klines.append(kline)
            
            # Maintain buffer size (keep twice the required length for safety)
            max_buffer_size = max(200, self.get_required_data_length() * 2)
            if len(self.klines) > max_buffer_size:
                self.klines = self.klines[-max_buffer_size:]
            
            # Process only if strategy is active and ready
            if not self.is_ready():
                return []
            
            # Generate signals
            signals = self.process_kline(kline)
            
            # Update metrics
            if signals:
                self.signals_generated += len(signals)
                self.last_signal_time = datetime.now(UTC)
                
                self.logger.info(
                    f"Generated {len(signals)} signals from kline",
                    extra_data={
                        "signal_count": len(signals),
                        "kline_close": float(kline.close_price),
                        "kline_time": kline.datetime.isoformat()
                    }
                )
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error processing kline: {e}")
            self.state = StrategyState.ERROR
            self.last_error = str(e)
            return []
    
    def add_mark_price(self, mark_price: MarkPriceData) -> List[StrategySignal]:
        """
        Add new mark price data and process it
        
        Args:
            mark_price: New mark price data
            
        Returns:
            List of generated signals
        """
        try:
            # Add to buffer  
            self.mark_prices.append(mark_price)
            
            # Maintain buffer size
            max_buffer_size = 100  # Keep last 100 mark prices
            if len(self.mark_prices) > max_buffer_size:
                self.mark_prices = self.mark_prices[-max_buffer_size:]
            
            # Process only if strategy is active and ready
            if not self.is_ready():
                return []
            
            # Generate signals
            signals = self.process_mark_price(mark_price)
            
            # Update metrics
            if signals:
                self.signals_generated += len(signals)
                self.last_signal_time = datetime.now(UTC)
                
                self.logger.info(
                    f"Generated {len(signals)} signals from mark price",
                    extra_data={
                        "signal_count": len(signals),
                        "mark_price": float(mark_price.mark_price)
                    }
                )
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error processing mark price: {e}")
            self.state = StrategyState.ERROR
            self.last_error = str(e)
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get strategy status information"""
        return {
            "strategy": self.__class__.__name__,
            "symbol": self.symbol,
            "state": self.state.value,
            "signals_generated": self.signals_generated,
            "last_signal_time": self.last_signal_time.isoformat() if self.last_signal_time else None,
            "last_error": self.last_error,
            "klines_count": len(self.klines),
            "mark_prices_count": len(self.mark_prices),
            "is_ready": self.is_ready(),
            "required_data_length": self.get_required_data_length()
        }
    
    def get_latest_kline(self) -> Optional[KlineData]:
        """Get the most recent kline"""
        return self.klines[-1] if self.klines else None
    
    def get_latest_mark_price(self) -> Optional[MarkPriceData]:
        """Get the most recent mark price"""
        return self.mark_prices[-1] if self.mark_prices else None
    
    def get_klines(self, count: Optional[int] = None) -> List[KlineData]:
        """
        Get recent klines
        
        Args:
            count: Number of recent klines to return (None for all)
            
        Returns:
            List of recent klines
        """
        if count is None:
            return self.klines.copy()
        return self.klines[-count:] if count > 0 else []