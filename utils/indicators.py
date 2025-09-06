"""Technical indicators for trading strategies using pandas-ta"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import List, Tuple, Optional
from decimal import Decimal
import math

from utils.data_models import KlineData


def _klines_to_dataframe(klines: List[KlineData]) -> pd.DataFrame:
    """Convert list of KlineData to pandas DataFrame for pandas-ta"""
    if not klines:
        return pd.DataFrame()
    
    data = {
        'open': [float(k.open_price) for k in klines],
        'high': [float(k.high_price) for k in klines],
        'low': [float(k.low_price) for k in klines],
        'close': [float(k.close_price) for k in klines],
        'volume': [float(k.volume) for k in klines]
    }
    
    df = pd.DataFrame(data)
    df.index = pd.to_datetime([k.datetime for k in klines])
    
    return df


def calculate_sma(values: List[float], period: int) -> float:
    """Calculate Simple Moving Average using pandas-ta"""
    if len(values) < period:
        return 0.0
    
    series = pd.Series(values)
    result = ta.sma(series, length=period)
    return float(result.iloc[-1]) if not pd.isna(result.iloc[-1]) else 0.0


def calculate_ema(values: List[float], period: int, previous_ema: Optional[float] = None) -> float:
    """Calculate Exponential Moving Average using pandas-ta"""
    if len(values) == 0:
        return 0.0
    
    series = pd.Series(values)
    result = ta.ema(series, length=period)
    return float(result.iloc[-1]) if not pd.isna(result.iloc[-1]) else 0.0


def calculate_vwap(klines: List[KlineData]) -> Tuple[float, float]:
    """
    Calculate Volume Weighted Average Price using pandas-ta
    
    Args:
        klines: List of kline data
        
    Returns:
        Tuple of (VWAP, VWAP_STD)
    """
    if not klines:
        return 0.0, 0.0
    
    df = _klines_to_dataframe(klines)
    if df.empty:
        return 0.0, 0.0
    
    # Calculate VWAP using pandas-ta
    vwap_result = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
    
    if vwap_result is None or pd.isna(vwap_result.iloc[-1]):
        return 0.0, 0.0
    
    vwap = float(vwap_result.iloc[-1])
    
    # Calculate VWAP standard deviation
    typical_prices = (df['high'] + df['low'] + df['close']) / 3
    vwap_series = pd.Series([vwap] * len(df), index=df.index)
    
    weighted_variance = ((typical_prices - vwap_series) ** 2 * df['volume']).sum() / df['volume'].sum()
    vwap_std = math.sqrt(weighted_variance) if weighted_variance > 0 else 0.0
    
    return vwap, vwap_std


def calculate_adx(klines: List[KlineData], period: int = 14) -> float:
    """
    Calculate Average Directional Index using pandas-ta
    
    Args:
        klines: List of kline data
        period: Period for ADX calculation
        
    Returns:
        ADX value
    """
    if len(klines) < period + 1:
        return 0.0
    
    df = _klines_to_dataframe(klines)
    if df.empty or len(df) < period + 1:
        return 0.0
    
    # Calculate ADX using pandas-ta
    adx_result = ta.adx(df['high'], df['low'], df['close'], length=period)
    
    if adx_result is None or adx_result.empty:
        return 0.0
    
    # ADX returns a DataFrame with columns: ADX_14, DMP_14, DMN_14
    adx_column = f'ADX_{period}'
    if adx_column in adx_result.columns:
        adx_value = adx_result[adx_column].iloc[-1]
        return float(adx_value) if not pd.isna(adx_value) else 0.0
    
    return 0.0


def calculate_bollinger_bands(values: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float]:
    """
    Calculate Bollinger Bands using pandas-ta
    
    Args:
        values: Price values
        period: Period for moving average
        std_dev: Standard deviation multiplier
        
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    if len(values) < period:
        return 0.0, 0.0, 0.0
    
    series = pd.Series(values)
    bb_result = ta.bbands(series, length=period, std=std_dev)
    
    if bb_result is None or bb_result.empty:
        return 0.0, 0.0, 0.0
    
    # Bollinger Bands returns columns: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0, BBP_20_2.0
    upper_col = f'BBU_{period}_{std_dev}'
    middle_col = f'BBM_{period}_{std_dev}'
    lower_col = f'BBL_{period}_{std_dev}'
    
    upper = float(bb_result[upper_col].iloc[-1]) if upper_col in bb_result.columns else 0.0
    middle = float(bb_result[middle_col].iloc[-1]) if middle_col in bb_result.columns else 0.0
    lower = float(bb_result[lower_col].iloc[-1]) if lower_col in bb_result.columns else 0.0
    
    return upper, middle, lower


def calculate_rsi(values: List[float], period: int = 14) -> float:
    """
    Calculate Relative Strength Index using pandas-ta
    
    Args:
        values: Price values
        period: Period for RSI calculation
        
    Returns:
        RSI value
    """
    if len(values) < period + 1:
        return 50.0  # Neutral RSI
    
    series = pd.Series(values)
    rsi_result = ta.rsi(series, length=period)
    
    if rsi_result is None or pd.isna(rsi_result.iloc[-1]):
        return 50.0
    
    return float(rsi_result.iloc[-1])


def calculate_macd(values: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[float, float, float]:
    """
    Calculate MACD using pandas-ta
    
    Args:
        values: Price values
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line EMA period
        
    Returns:
        Tuple of (MACD line, Signal line, Histogram)
    """
    if len(values) < slow_period:
        return 0.0, 0.0, 0.0
    
    series = pd.Series(values)
    macd_result = ta.macd(series, fast=fast_period, slow=slow_period, signal=signal_period)
    
    if macd_result is None or macd_result.empty:
        return 0.0, 0.0, 0.0
    
    # MACD returns columns: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
    macd_col = f'MACD_{fast_period}_{slow_period}_{signal_period}'
    signal_col = f'MACDs_{fast_period}_{slow_period}_{signal_period}'
    histogram_col = f'MACDh_{fast_period}_{slow_period}_{signal_period}'
    
    macd_line = float(macd_result[macd_col].iloc[-1]) if macd_col in macd_result.columns else 0.0
    signal_line = float(macd_result[signal_col].iloc[-1]) if signal_col in macd_result.columns else 0.0
    histogram = float(macd_result[histogram_col].iloc[-1]) if histogram_col in macd_result.columns else 0.0
    
    return macd_line, signal_line, histogram


def calculate_volatility(klines: List[KlineData], period: int = 20) -> float:
    """
    Calculate price volatility using pandas-ta
    
    Args:
        klines: List of kline data
        period: Period for volatility calculation
        
    Returns:
        Volatility value (annualized)
    """
    if len(klines) < period + 1:
        return 0.0
    
    df = _klines_to_dataframe(klines)
    if df.empty or len(df) < period + 1:
        return 0.0
    
    # Calculate log returns
    log_returns = (df['close'] / df['close'].shift(1)).apply(np.log)
    
    # Calculate rolling standard deviation
    volatility = log_returns.rolling(window=period).std().iloc[-1]
    
    if pd.isna(volatility):
        return 0.0
    
    # Annualize volatility (assuming 1-minute data: 365 * 24 * 60 periods per year)
    return float(volatility * math.sqrt(365 * 24 * 60))


def check_volatility_spike(klines: List[KlineData], lookback_seconds: int = 5, threshold: float = 0.02) -> bool:
    """
    Check if there was a volatility spike in recent data
    
    Args:
        klines: List of kline data (1-minute intervals)
        lookback_seconds: How many seconds to look back
        threshold: Volatility threshold (2% default)
        
    Returns:
        True if volatility spike detected
    """
    if len(klines) < 2:
        return False
    
    # For 1-minute data, we check the last few minutes
    lookback_minutes = max(1, lookback_seconds // 60)
    recent_klines = klines[-lookback_minutes-1:]
    
    if len(recent_klines) < 2:
        return False
    
    max_change = 0.0
    for i in range(1, len(recent_klines)):
        prev_close = float(recent_klines[i-1].close_price)
        curr_close = float(recent_klines[i].close_price)
        
        if prev_close > 0:
            change = abs((curr_close - prev_close) / prev_close)
            max_change = max(max_change, change)
    
    return max_change > threshold