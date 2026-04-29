"""
Technical Indicators Module
Vectorized calculations for all technical indicators
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(window=period).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def bollinger_bands(series: pd.Series, period: int = 20, std: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands"""
    middle = sma(series, period)
    std_dev = series.rolling(window=period).std()
    
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    
    return upper, middle, lower


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD Indicator"""
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def vwap(df: pd.DataFrame) -> pd.Series:
    """Volume Weighted Average Price"""
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    return (typical_price * df['volume']).cumsum() / df['volume'].cumsum()


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    tr = atr(df, 1)
    
    atr_period = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr_period)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr_period)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx_line = dx.rolling(window=period).mean()
    
    return adx_line


def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """Supertrend Indicator"""
    hl_avg = (df['high'] + df['low']) / 2
    atr_val = atr(df, period)
    
    upper_band = hl_avg + (multiplier * atr_val)
    lower_band = hl_avg - (multiplier * atr_val)
    
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1
    
    for i in range(1, len(df)):
        if df['close'].iloc[i] > supertrend.iloc[i-1]:
            direction.iloc[i] = 1
            supertrend.iloc[i] = lower_band.iloc[i]
        elif df['close'].iloc[i] < supertrend.iloc[i-1]:
            direction.iloc[i] = -1
            supertrend.iloc[i] = upper_band.iloc[i]
        else:
            direction.iloc[i] = direction.iloc[i-1]
            if direction.iloc[i] == 1:
                supertrend.iloc[i] = lower_band.iloc[i]
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
    
    return supertrend, direction


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all indicators at once"""
    df = df.copy()
    
    # Moving averages
    df['ema_9'] = ema(df['close'], 9)
    df['ema_21'] = ema(df['close'], 21)
    df['ema_50'] = ema(df['close'], 50)
    df['sma_200'] = sma(df['close'], 200)
    
    # Momentum
    df['rsi'] = rsi(df['close'], 14)
    df['atr'] = atr(df, 14)
    
    # Trend
    df['adx'] = adx(df, 14)
    df['supertrend'], df['supertrend_dir'] = supertrend(df, 10, 3.0)
    
    # Bollinger Bands
    df['bb_upper'], df['bb_middle'], df['bb_lower'] = bollinger_bands(df['close'], 20, 2)
    
    # MACD
    df['macd'], df['macd_signal'], df['macd_hist'] = macd(df['close'], 12, 26, 9)
    
    # VWAP
    if 'volume' in df.columns:
        df['vwap'] = vwap(df)
    
    return df
