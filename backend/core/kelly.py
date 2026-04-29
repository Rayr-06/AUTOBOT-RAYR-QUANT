"""
Kelly Criterion - Optimal Position Sizing
Maximizes long-term growth rate
"""
import numpy as np

class KellyPositionSizer:
    def __init__(self, max_kelly_fraction=0.5):
        """
        max_kelly_fraction: Never bet more than 50% of Kelly (safety)
        """
        self.max_kelly = max_kelly_fraction
    
    def calculate_size(self, win_rate, avg_win, avg_loss, capital):
        """
        Kelly Formula: f = (p*b - q) / b
        where:
        - p = win probability
        - q = loss probability (1-p)
        - b = win/loss ratio
        """
        if avg_loss == 0 or win_rate == 0:
            return capital * 0.02  # Default to 2%
        
        win_loss_ratio = abs(avg_win / avg_loss)
        loss_rate = 1 - win_rate
        
        # Kelly fraction
        kelly_fraction = (win_rate * win_loss_ratio - loss_rate) / win_loss_ratio
        
        # Apply safety factor (half Kelly)
        safe_fraction = kelly_fraction * self.max_kelly
        
        # Never risk more than 3% per trade
        safe_fraction = min(safe_fraction, 0.03)
        
        # Never risk less than 0.5%
        safe_fraction = max(safe_fraction, 0.005)
        
        return capital * safe_fraction
    
    def get_historical_stats(self, trades):
        """
        Calculate win rate and avg win/loss from trade history
        """
        if not trades or len(trades) < 10:
            # Default conservative values
            return {
                'win_rate': 0.55,
                'avg_win': 0.02,
                'avg_loss': 0.015
            }
        
        wins = [t for t in trades if t.get('pnl', 0) > 0]
        losses = [t for t in trades if t.get('pnl', 0) < 0]
        
        win_rate = len(wins) / len(trades) if trades else 0.55
        
        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0.02
        avg_loss = abs(np.mean([t['pnl'] for t in losses])) if losses else 0.015
        
        return {
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss
        }