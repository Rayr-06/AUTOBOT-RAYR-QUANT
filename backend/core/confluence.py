"""
Confluence Scoring Engine
8-dimensional technical analysis scoring system
"""

import pandas as pd
import numpy as np
from .indicators import calculate_all_indicators


class ConfluenceScorer:
    """
    Multi-dimensional confluence scoring
    Score range: 0-100 (BUY signal >= 72)
    """
    
    def __init__(self):
        self.weights = {
            'trend': 0.20,
            'momentum': 0.15,
            'volume': 0.15,
            'vcp': 0.10,
            'structure': 0.15,
            'supertrend': 0.10,
            'support': 0.10,
            'risk_reward': 0.05
        }
    
    
    def score_trend(self, df: pd.DataFrame) -> float:
        """Trend strength (0-100)"""
        last = df.iloc[-1]
        score = 0
        
        # EMA alignment (40 points)
        if last['close'] > last['ema_9'] > last['ema_21'] > last['ema_50']:
            score += 40
        elif last['close'] > last['ema_9'] > last['ema_21']:
            score += 25
        elif last['close'] > last['ema_9']:
            score += 10
        
        # ADX strength (30 points)
        adx = last['adx']
        if adx > 40:
            score += 30
        elif adx > 25:
            score += 20
        elif adx > 20:
            score += 10
        
        # Price above 200 SMA (30 points)
        if last['close'] > last['sma_200']:
            score += 30
        
        return min(score, 100)
    
    
    def score_momentum(self, df: pd.DataFrame) -> float:
        """Momentum strength (0-100)"""
        last = df.iloc[-1]
        prev = df.iloc[-2]
        score = 0
        
        # RSI (50 points)
        rsi = last['rsi']
        if 50 < rsi < 70:
            score += 50
        elif 40 < rsi <= 50:
            score += 35
        elif 30 < rsi <= 40:
            score += 20
        
        # MACD (50 points)
        if last['macd'] > last['macd_signal'] and last['macd_hist'] > 0:
            score += 50
        elif last['macd'] > last['macd_signal']:
            score += 30
        
        return min(score, 100)
    
    
    def score_volume(self, df: pd.DataFrame) -> float:
        """Volume analysis (0-100)"""
        if 'volume' not in df.columns:
            return 50
        
        last = df.iloc[-1]
        avg_volume = df['volume'].tail(20).mean()
        score = 0
        
        # Volume surge (60 points)
        vol_ratio = last['volume'] / avg_volume
        if vol_ratio > 2.0:
            score += 60
        elif vol_ratio > 1.5:
            score += 40
        elif vol_ratio > 1.2:
            score += 20
        
        # Price-volume confirmation (40 points)
        if last['close'] > last['open'] and last['volume'] > avg_volume:
            score += 40
        
        return min(score, 100)
    
    
    def score_vcp(self, df: pd.DataFrame) -> float:
        """Volatility Contraction Pattern (0-100)"""
        if len(df) < 50:
            return 50
        
        score = 0
        
        # ATR contraction (60 points)
        current_atr = df['atr'].iloc[-1]
        avg_atr = df['atr'].tail(50).mean()
        
        if current_atr < avg_atr * 0.7:
            score += 60
        elif current_atr < avg_atr * 0.85:
            score += 40
        
        # Tightening range (40 points)
        recent_range = (df['high'].tail(10) - df['low'].tail(10)).mean()
        older_range = (df['high'].iloc[-30:-10] - df['low'].iloc[-30:-10]).mean()
        
        if recent_range < older_range * 0.6:
            score += 40
        elif recent_range < older_range * 0.8:
            score += 20
        
        return min(score, 100)
    
    
    def score_structure(self, df: pd.DataFrame) -> float:
        """Price structure (0-100)"""
        last = df.iloc[-1]
        score = 0
        
        # Bollinger position (50 points)
        bb_position = (last['close'] - last['bb_lower']) / (last['bb_upper'] - last['bb_lower'])
        if 0.5 < bb_position < 0.8:
            score += 50
        elif bb_position > 0.5:
            score += 30
        
        # Higher highs/lows (50 points)
        recent_highs = df['high'].tail(10)
        recent_lows = df['low'].tail(10)
        
        if recent_highs.iloc[-1] > recent_highs.iloc[-5] and recent_lows.iloc[-1] > recent_lows.iloc[-5]:
            score += 50
        
        return min(score, 100)
    
    
    def score_supertrend(self, df: pd.DataFrame) -> float:
        """Supertrend signal (0-100)"""
        last = df.iloc[-1]
        
        if last['supertrend_dir'] == 1:  # Bullish
            return 100
        else:
            return 0
    
    
    def score_support(self, df: pd.DataFrame) -> float:
        """Support/Resistance proximity (0-100)"""
        last = df.iloc[-1]
        score = 0
        
        # Near support levels (100 points)
        close = last['close']
        
        # EMA support
        if abs(close - last['ema_21']) / close < 0.02:
            score += 50
        
        # Recent swing lows
        recent_lows = df['low'].tail(20)
        support = recent_lows.min()
        
        if abs(close - support) / close < 0.03:
            score += 50
        
        return min(score, 100)
    
    
    def score_risk_reward(self, df: pd.DataFrame) -> float:
        """Risk/Reward ratio (0-100)"""
        last = df.iloc[-1]
        
        # Entry
        entry = last['close']
        
        # Stop loss (below recent swing low or ATR)
        recent_low = df['low'].tail(10).min()
        atr_stop = entry - (2 * last['atr'])
        stop_loss = max(recent_low, atr_stop)
        
        # Target (resistance or ATR multiple)
        recent_high = df['high'].tail(20).max()
        atr_target = entry + (3 * last['atr'])
        target = min(recent_high, atr_target)
        
        # Calculate R:R
        risk = entry - stop_loss
        reward = target - entry
        
        if risk > 0:
            rr_ratio = reward / risk
            
            if rr_ratio >= 3:
                return 100
            elif rr_ratio >= 2:
                return 75
            elif rr_ratio >= 1.5:
                return 50
            else:
                return 25
        
        return 0
    
    
    def calculate_score(self, df: pd.DataFrame) -> dict:
        """Calculate total confluence score"""
        # Ensure all indicators are calculated
        df = calculate_all_indicators(df)
        
        # Calculate individual scores
        scores = {
            'trend': self.score_trend(df),
            'momentum': self.score_momentum(df),
            'volume': self.score_volume(df),
            'vcp': self.score_vcp(df),
            'structure': self.score_structure(df),
            'supertrend': self.score_supertrend(df),
            'support': self.score_support(df),
            'risk_reward': self.score_risk_reward(df)
        }
        
        # Weighted total
        total_score = sum(scores[dim] * self.weights[dim] for dim in scores)
        
        # Signal
        signal = "BUY" if total_score >= 72 else "HOLD" if total_score >= 50 else "WAIT"
        
        return {
            'total_score': round(total_score, 2),
            'signal': signal,
            'breakdown': scores,
            'timestamp': df.iloc[-1].name if hasattr(df.iloc[-1].name, 'isoformat') else None
        }
