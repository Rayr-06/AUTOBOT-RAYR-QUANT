"""
Market Regime Detection
Determines if market is: TRENDING, CHOPPY, or VOLATILE
"""
import pandas as pd
import numpy as np

class RegimeDetector:
    def detect(self, df):
        """
        Returns: 'TRENDING', 'CHOPPY', or 'VOLATILE'
        """
        # ADX for trend strength
        adx = self._calculate_adx(df)
        
        # Volatility (ATR / Price)
        atr = df['atr'].iloc[-1] if 'atr' in df else 0
        price = df['close'].iloc[-1]
        volatility_pct = (atr / price) * 100
        
        # Recent price action
        returns = df['close'].pct_change().tail(20)
        volatility_recent = returns.std() * 100
        
        # Classification
        if adx > 25 and volatility_pct < 4:
            return {
                'regime': 'TRENDING',
                'strength': adx,
                'volatility': volatility_pct,
                'best_strategy': 'AGGRESSIVE'
            }
        elif volatility_pct > 6 or volatility_recent > 3:
            return {
                'regime': 'VOLATILE',
                'strength': adx,
                'volatility': volatility_pct,
                'best_strategy': 'CONSERVATIVE'
            }
        else:
            return {
                'regime': 'CHOPPY',
                'strength': adx,
                'volatility': volatility_pct,
                'best_strategy': 'BALANCED'
            }
    
    def _calculate_adx(self, df, period=14):
        """Calculate Average Directional Index"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        up = high - high.shift()
        down = low.shift() - low
        
        plus_dm = np.where((up > down) & (up > 0), up, 0)
        minus_dm = np.where((down > up) & (down > 0), down, 0)
        
        # Smooth
        atr = tr.rolling(period).mean()
        plus_di = 100 * pd.Series(plus_dm).rolling(period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(period).mean() / atr
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        
        return adx.iloc[-1] if len(adx) > 0 else 20