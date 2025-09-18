"""VWAP Mean Reversion Strategy with ADX Filter"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, UTC, timedelta

from strategies.base import BaseStrategy, StrategySignal
from database.models import SignalType
from utils.data_models import KlineData, MarkPriceData
from utils.indicators import (
    calculate_vwap, calculate_adx, calculate_volatility, 
    check_volatility_spike, calculate_rsi
)


class VWAPStrategy(BaseStrategy):
    """
    VWAP Mean Reversion Strategy with ADX Filter
    
    Strategy Logic:
    1. Calculate VWAP and standard deviation bands
    2. Use ADX < 20 to filter for sideways markets
    3. Generate BUY signals when price is below lower VWAP band
    4. Generate SELL signals when price is above upper VWAP band
    5. Safety mechanism: halt trading for 10 minutes after volatility spike
    """
    
    @classmethod
    def get_strategy_name(cls) -> str:
        return "vwap"

    def __init__(self, symbol: str, config: Dict[str, Any]):
        super().__init__(symbol, config)
        
        # Strategy state
        self.last_signal_time: Optional[datetime] = None
        self.volatility_halt_until: Optional[datetime] = None
        
        # VWAP calculation state
        self.current_vwap = 0.0
        self.current_vwap_std = 0.0
        self.current_adx = 0.0
        
        self.logger.info(f"VWAP strategy initialized with config: {config}")
    
    def _validate_config(self) -> None:
        """Validate strategy configuration"""
        required_params = [
            'vwap_period', 'vwap_std_multiplier', 'adx_period', 'adx_threshold',
            'target_profit_pct', 'stop_loss_pct', 'volatility_threshold',
            'volatility_halt_minutes', 'min_confidence'
        ]
        
        for param in required_params:
            if param not in self.config:
                raise ValueError(f"Missing required config parameter: {param}")
        
        # Validate parameter ranges
        if self.config['vwap_period'] < 10:
            raise ValueError("VWAP period must be at least 10")
        
        if self.config['adx_threshold'] < 0 or self.config['adx_threshold'] > 50:
            raise ValueError("ADX threshold must be between 0 and 50")
        
        if self.config['target_profit_pct'] <= 0:
            raise ValueError("Target profit percentage must be positive")
        
        if self.config['stop_loss_pct'] <= 0:
            raise ValueError("Stop loss percentage must be positive")
    
    def get_required_data_length(self) -> int:
        """Return minimum klines needed for strategy"""
        return max(self.config['vwap_period'], self.config['adx_period']) + 10
    
    def _is_in_volatility_halt(self) -> bool:
        """Check if strategy is in volatility halt period"""
        if self.volatility_halt_until is None:
            return False
        
        return datetime.now(UTC) < self.volatility_halt_until
    
    def _check_volatility_spike(self, kline: KlineData) -> bool:
        """Check for volatility spike and set halt if detected"""
        if check_volatility_spike(
            self.klines, 
            lookback_seconds=5,
            threshold=self.config['volatility_threshold']
        ):
            self.volatility_halt_until = datetime.now(UTC) + timedelta(
                minutes=self.config['volatility_halt_minutes']
            )
            
            self.logger.warning(
                f"Volatility spike detected, halting trading for {self.config['volatility_halt_minutes']} minutes",
                extra_data={
                    "halt_until": self.volatility_halt_until.isoformat(),
                    "current_price": float(kline.close_price)
                }
            )
            return True
        
        return False
    
    def _calculate_indicators(self) -> Dict[str, float]:
        """Calculate all technical indicators"""
        if len(self.klines) < self.get_required_data_length():
            return {}
        
        # Calculate VWAP
        vwap_klines = self.klines[-self.config['vwap_period']:]
        self.current_vwap, self.current_vwap_std = calculate_vwap(vwap_klines)
        
        # Calculate ADX
        adx_klines = self.klines[-self.config['adx_period']-1:]
        self.current_adx = calculate_adx(adx_klines, self.config['adx_period'])
        
        # Calculate additional indicators
        close_prices = [float(k.close_price) for k in self.klines[-20:]]
        current_rsi = calculate_rsi(close_prices) if len(close_prices) >= 14 else 50.0
        current_volatility = calculate_volatility(self.klines[-20:]) if len(self.klines) >= 20 else 0.0
        
        return {
            'vwap': self.current_vwap,
            'vwap_std': self.current_vwap_std,
            'adx': self.current_adx,
            'rsi': current_rsi,
            'volatility': current_volatility,
            'upper_band': self.current_vwap + (self.current_vwap_std * self.config['vwap_std_multiplier']),
            'lower_band': self.current_vwap - (self.current_vwap_std * self.config['vwap_std_multiplier'])
        }
    
    def _generate_buy_signal(self, kline: KlineData, indicators: Dict[str, float]) -> Optional[StrategySignal]:
        """Generate BUY signal if conditions are met"""
        current_price = float(kline.close_price)
        lower_band = indicators['lower_band']
        
        # Check buy conditions
        conditions = {
            'price_below_lower_band': current_price < lower_band,
            'adx_filter': indicators['adx'] < self.config['adx_threshold'],
            'not_oversold': indicators['rsi'] > 25,  # Avoid extreme oversold
            'sufficient_deviation': (lower_band - current_price) / current_price > 0.001  # At least 0.1%
        }
        
        # Log condition checks
        self.logger.debug(
            f"BUY signal conditions: {conditions}",
            extra_data={
                "current_price": current_price,
                "lower_band": lower_band,
                "adx": indicators['adx'],
                "rsi": indicators['rsi']
            }
        )
        
        if all(conditions.values()):
            # Calculate confidence based on signal strength
            price_deviation = (lower_band - current_price) / current_price
            adx_strength = max(0, (self.config['adx_threshold'] - indicators['adx']) / self.config['adx_threshold'])
            confidence = min(0.95, 0.5 + (price_deviation * 50) + (adx_strength * 0.3))
            
            if confidence >= self.config['min_confidence']:
                return StrategySignal(
                    symbol=self.symbol,
                    signal_type=SignalType.BUY,
                    price=Decimal(str(current_price)),
                    confidence=Decimal(str(confidence)),
                    market_conditions={
                        'vwap': indicators['vwap'],
                        'adx': indicators['adx'],
                        'rsi': indicators['rsi'],
                        'volatility': indicators['volatility']
                    },
                    indicators=indicators.copy(),
                    notes=f"Price {price_deviation:.3%} below VWAP lower band, ADX {indicators['adx']:.1f} indicates sideways market"
                )
        
        return None
    
    def _generate_sell_signal(self, kline: KlineData, indicators: Dict[str, float]) -> Optional[StrategySignal]:
        """Generate SELL signal if conditions are met"""
        current_price = float(kline.close_price)
        upper_band = indicators['upper_band']
        
        # Check sell conditions
        conditions = {
            'price_above_upper_band': current_price > upper_band,
            'adx_filter': indicators['adx'] < self.config['adx_threshold'],
            'not_overbought': indicators['rsi'] < 75,  # Avoid extreme overbought
            'sufficient_deviation': (current_price - upper_band) / current_price > 0.001  # At least 0.1%
        }
        
        # Log condition checks
        self.logger.debug(
            f"SELL signal conditions: {conditions}",
            extra_data={
                "current_price": current_price,
                "upper_band": upper_band,
                "adx": indicators['adx'],
                "rsi": indicators['rsi']
            }
        )
        
        if all(conditions.values()):
            # Calculate confidence based on signal strength
            price_deviation = (current_price - upper_band) / current_price
            adx_strength = max(0, (self.config['adx_threshold'] - indicators['adx']) / self.config['adx_threshold'])
            confidence = min(0.95, 0.5 + (price_deviation * 50) + (adx_strength * 0.3))
            
            if confidence >= self.config['min_confidence']:
                return StrategySignal(
                    symbol=self.symbol,
                    signal_type=SignalType.SELL,
                    price=Decimal(str(current_price)),
                    confidence=Decimal(str(confidence)),
                    market_conditions={
                        'vwap': indicators['vwap'],
                        'adx': indicators['adx'],
                        'rsi': indicators['rsi'],
                        'volatility': indicators['volatility']
                    },
                    indicators=indicators.copy(),
                    notes=f"Price {price_deviation:.3%} above VWAP upper band, ADX {indicators['adx']:.1f} indicates sideways market"
                )
        
        return None
    
    def process_kline(self, kline: KlineData) -> List[StrategySignal]:
        """Process kline data and generate signals"""
        if not kline.is_closed:
            return []  # Only process closed klines
        
        # Check volatility spike
        if self._check_volatility_spike(kline):
            return []
        
        # Check if in volatility halt
        if self._is_in_volatility_halt():
            return []
        
        # Calculate indicators
        indicators = self._calculate_indicators()
        if not indicators:
            return []  # Not enough data
        
        signals = []
        current_price = float(kline.close_price)
        
        # Check signal timing (avoid too frequent signals)
        if self.last_signal_time:
            time_since_last = datetime.now(UTC) - self.last_signal_time
            if time_since_last.total_seconds() < 60:  # Minimum 1 minute between signals
                return []
        
        # Generate signals
        buy_signal = self._generate_buy_signal(kline, indicators)
        if buy_signal:
            signals.append(buy_signal)
            self.last_signal_time = datetime.now(UTC)
        
        sell_signal = self._generate_sell_signal(kline, indicators)
        if sell_signal:
            signals.append(sell_signal)
            self.last_signal_time = datetime.now(UTC)
        
        # Log strategy state
        if signals:
            self.logger.info(
                f"Generated {len(signals)} signals",
                extra_data={
                    "signals": [s.signal_type.value for s in signals],
                    "price": current_price,
                    "vwap": indicators['vwap'],
                    "upper_band": indicators['upper_band'],
                    "lower_band": indicators['lower_band'],
                    "adx": indicators['adx']
                }
            )
        
        return signals
    
    def process_mark_price(self, mark_price: MarkPriceData) -> List[StrategySignal]:
        """Process mark price data (not used for VWAP strategy)"""
        # VWAP strategy primarily uses kline data
        # Mark price could be used for additional validation if needed
        return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed strategy status"""
        base_status = super().get_status()
        
        vwap_status = {
            'current_vwap': self.current_vwap,
            'current_vwap_std': self.current_vwap_std,
            'current_adx': self.current_adx,
            'upper_band': self.current_vwap + (self.current_vwap_std * self.config['vwap_std_multiplier']),
            'lower_band': self.current_vwap - (self.current_vwap_std * self.config['vwap_std_multiplier']),
            'volatility_halt_until': self.volatility_halt_until.isoformat() if self.volatility_halt_until else None,
            'in_volatility_halt': self._is_in_volatility_halt(),
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None
        }
        
        base_status.update(vwap_status)
        return base_status