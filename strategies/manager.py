from typing import Dict, List, Optional, Type, Any, Callable
from datetime import datetime, UTC
import importlib
import inspect
from pathlib import Path

from strategies.base import BaseStrategy, StrategyState, StrategySignal
from utils.data_models import KlineData, MarkPriceData
from utils.logging import get_logger, TradingLoggerAdapter
from config.symbols import SymbolManager


class StrategyRegistry:
    """Registry for all available strategies"""
    
    def __init__(self):
        self.strategies: Dict[str, Type[BaseStrategy]] = {}
        self.logger: TradingLoggerAdapter = get_logger("strategy_registry")
    
    def register(self, strategy_class: Type[BaseStrategy]) -> None:
        """
        Register a strategy class
        
        Args:
            strategy_class: Strategy class to register
        """
        strategy_name = strategy_class.get_strategy_name()
        if strategy_name in self.strategies:
            self.logger.warning(f"Strategy {strategy_name} already registered, overwriting")
        
        self.strategies[strategy_name] = strategy_class
        self.logger.info(f"Registered strategy: {strategy_name}")
    
    def get_strategy(self, strategy_name: str) -> Optional[Type[BaseStrategy]]:
        """Get strategy class by name"""
        return self.strategies.get(strategy_name)
    
    def list_strategies(self) -> List[str]:
        """List all registered strategy names"""
        return list(self.strategies.keys())
    
    def auto_discover_strategies(self, strategies_dir: Path = None) -> int:
        """
        Automatically discover and register strategies from the strategies directory
        
        Args:
            strategies_dir: Directory to search for strategies (defaults to strategies/)
            
        Returns:
            Number of strategies discovered and registered
        """
        if strategies_dir is None:
            strategies_dir = Path(__file__).parent
        
        discovered_count = 0
        
        for py_file in strategies_dir.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name in ["base.py", "manager.py"]:
                continue
                
            try:
                # Import the module
                module_name = f"strategies.{py_file.stem}"
                module = importlib.import_module(module_name)
                
                # Find strategy classes in the module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseStrategy) and 
                        obj != BaseStrategy):
                        self.register(obj)
                        discovered_count += 1
                        
            except Exception as e:
                self.logger.error(f"Failed to import strategy from {py_file}: {e}")
        
        self.logger.info(f"Auto-discovered {discovered_count} strategies")
        return discovered_count


class StrategyInstance:
    """Wrapper for strategy instance with additional metadata"""
    
    def __init__(self, strategy: BaseStrategy, config: Dict[str, Any]):
        self.strategy = strategy
        self.config = config
        self.created_at = datetime.now(UTC)
        self.last_activity = datetime.now(UTC)
        
        # Performance metrics
        self.total_signals = 0
        self.successful_signals = 0
        self.error_count = 0
        
        # Signal callbacks
        self.signal_callbacks: List[Callable[[StrategySignal], None]] = []
    
    def add_signal_callback(self, callback: Callable[[StrategySignal], None]) -> None:
        """Add callback for when signals are generated"""
        self.signal_callbacks.append(callback)
    
    def _handle_signals(self, signals: List[StrategySignal]) -> None:
        """Handle generated signals by calling callbacks"""
        self.total_signals += len(signals)
        self.last_activity = datetime.now(UTC)
        
        for signal in signals:
            for callback in self.signal_callbacks:
                try:
                    callback(signal)
                except Exception as e:
                    self.strategy.logger.error(f"Signal callback error: {e}")
                    self.error_count += 1
    
    def process_kline(self, kline: KlineData) -> List[StrategySignal]:
        """Process kline and handle signals"""
        try:
            signals = self.strategy.add_kline(kline)
            self._handle_signals(signals)
            return signals
        except Exception as e:
            self.error_count += 1
            self.strategy.logger.error(f"Error processing kline: {e}")
            return []
    
    def process_mark_price(self, mark_price: MarkPriceData) -> List[StrategySignal]:
        """Process mark price and handle signals"""
        try:
            signals = self.strategy.add_mark_price(mark_price)
            self._handle_signals(signals)
            return signals
        except Exception as e:
            self.error_count += 1
            self.strategy.logger.error(f"Error processing mark price: {e}")
            return []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get strategy performance metrics"""
        uptime = datetime.now(UTC) - self.created_at
        
        return {
            "strategy": self.strategy.__class__.__name__,
            "symbol": self.strategy.symbol,
            "state": self.strategy.state.value,
            "uptime_seconds": uptime.total_seconds(),
            "total_signals": self.total_signals,
            "successful_signals": self.successful_signals,
            "error_count": self.error_count,
            "last_activity": self.last_activity.isoformat(),
            "signal_rate": self.total_signals / max(uptime.total_seconds() / 3600, 0.01),  # per hour
            "error_rate": self.error_count / max(self.total_signals, 1)
        }


class StrategyManager:
    """Manages all strategy instances and their lifecycle"""
    
    def __init__(self, symbol_manager: SymbolManager = None):
        self.registry = StrategyRegistry()
        self.symbol_manager = symbol_manager or SymbolManager()
        self.logger: TradingLoggerAdapter = get_logger("strategy_manager")
        
        # Active strategy instances
        self.instances: Dict[str, StrategyInstance] = {}  # key: f"{strategy_name}_{symbol}"
        
        # Global signal callbacks
        self.global_signal_callbacks: List[Callable[[StrategySignal], None]] = []
        
        # Auto-discover strategies
        self.registry.auto_discover_strategies()
        
        self.logger.info("Strategy manager initialized")
    
    def add_global_signal_callback(self, callback: Callable[[StrategySignal], None]) -> None:
        """Add global callback for all strategy signals"""
        self.global_signal_callbacks.append(callback)
    
    def create_strategy(self, strategy_name: str, symbol: str, config: Dict[str, Any] = None) -> Optional[str]:
        """
        Create and start a strategy instance
        
        Args:
            strategy_name: Name of the strategy class
            symbol: Trading symbol
            config: Strategy configuration (will merge with symbol config)
            
        Returns:
            Strategy instance key if successful, None otherwise
        """
        try:
            # Get strategy class
            strategy_class = self.registry.get_strategy(strategy_name)
            if not strategy_class:
                self.logger.error(f"Strategy {strategy_name} not found in registry")
                return None
            
            # Load symbol configuration
            symbol_config = self.symbol_manager.load_symbol_config(symbol, strategy_class.get_strategy_name())
            if not symbol_config or not symbol_config.enabled:
                self.logger.error(f"Symbol {symbol} not enabled for strategy {strategy_name}")
                return None
            
            # Merge configurations
            merged_config = symbol_config.strategy_params.copy()
            if config:
                merged_config.update(config)
            
            # Create strategy instance
            strategy = strategy_class(symbol, merged_config)
            
            # Create wrapper instance
            instance_key = f"{strategy_name}_{symbol}"
            instance = StrategyInstance(strategy, merged_config)
            
            # Add global signal callbacks
            for callback in self.global_signal_callbacks:
                instance.add_signal_callback(callback)
            
            # Start strategy
            if strategy.start():
                self.instances[instance_key] = instance
                self.logger.info(f"Created and started strategy instance: {instance_key}")
                return instance_key
            else:
                self.logger.error(f"Failed to start strategy instance: {instance_key}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating strategy {strategy_name} for {symbol}: {e}")
            return None
    
    def stop_strategy(self, instance_key: str) -> bool:
        """Stop and remove a strategy instance"""
        try:
            if instance_key not in self.instances:
                self.logger.warning(f"Strategy instance {instance_key} not found")
                return False
            
            instance = self.instances[instance_key]
            success = instance.strategy.stop()
            
            if success:
                del self.instances[instance_key]
                self.logger.info(f"Stopped and removed strategy instance: {instance_key}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error stopping strategy {instance_key}: {e}")
            return False
    
    def pause_strategy(self, instance_key: str) -> bool:
        """Pause a strategy instance"""
        if instance_key not in self.instances:
            self.logger.warning(f"Strategy instance {instance_key} not found")
            return False
        
        return self.instances[instance_key].strategy.pause()
    
    def resume_strategy(self, instance_key: str) -> bool:
        """Resume a paused strategy instance"""
        if instance_key not in self.instances:
            self.logger.warning(f"Strategy instance {instance_key} not found")
            return False
        
        return self.instances[instance_key].strategy.start()
    
    def process_kline(self, kline: KlineData) -> Dict[str, List[StrategySignal]]:
        """
        Process kline data for all relevant strategies
        
        Args:
            kline: Kline data to process
            
        Returns:
            Dictionary mapping instance keys to generated signals
        """
        results = {}
        
        for instance_key, instance in self.instances.items():
            if instance.strategy.symbol == kline.symbol:
                signals = instance.process_kline(kline)
                if signals:
                    results[instance_key] = signals
        
        return results
    
    def process_mark_price(self, mark_price: MarkPriceData) -> Dict[str, List[StrategySignal]]:
        """
        Process mark price data for all relevant strategies
        
        Args:
            mark_price: Mark price data to process
            
        Returns:
            Dictionary mapping instance keys to generated signals
        """
        results = {}
        
        for instance_key, instance in self.instances.items():
            if instance.strategy.symbol == mark_price.symbol:
                signals = instance.process_mark_price(mark_price)
                if signals:
                    results[instance_key] = signals
        
        return results
    
    def get_strategy_status(self, instance_key: str = None) -> Dict[str, Any]:
        """
        Get status of strategy instances
        
        Args:
            instance_key: Specific instance to get status for (None for all)
            
        Returns:
            Strategy status information
        """
        if instance_key:
            if instance_key not in self.instances:
                return {"error": f"Strategy instance {instance_key} not found"}
            
            instance = self.instances[instance_key]
            return {
                "strategy_status": instance.strategy.get_status(),
                "performance_metrics": instance.get_performance_metrics()
            }
        
        # Return status for all instances
        return {
            "total_instances": len(self.instances),
            "active_instances": len([i for i in self.instances.values() 
                                   if i.strategy.state == StrategyState.ACTIVE]),
            "instances": {
                key: {
                    "strategy_status": instance.strategy.get_status(),
                    "performance_metrics": instance.get_performance_metrics()
                }
                for key, instance in self.instances.items()
            }
        }
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available strategy classes"""
        return self.registry.list_strategies()
    
    def restart_failed_strategies(self) -> int:
        """Restart strategies that are in ERROR state"""
        restarted_count = 0
        
        for instance_key, instance in list(self.instances.items()):
            if instance.strategy.state == StrategyState.ERROR:
                self.logger.info(f"Restarting failed strategy: {instance_key}")
                
                if instance.strategy.start():
                    restarted_count += 1
                    self.logger.info(f"Successfully restarted: {instance_key}")
                else:
                    self.logger.error(f"Failed to restart: {instance_key}")
        
        return restarted_count


# Global strategy manager instance
strategy_manager = StrategyManager()