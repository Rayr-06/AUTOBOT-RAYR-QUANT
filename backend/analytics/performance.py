"""
Performance Analytics Engine
Calculates all key metrics
"""
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

class PerformanceAnalyzer:
    def __init__(self):
        self.trades_file = Path("data/trades/paper_trades.json")
    
    def get_all_metrics(self):
        """Calculate all performance metrics"""
        trades = self._load_trades()
        
        if not trades or len(trades) < 2:
            return self._default_metrics()
        
        # Calculate metrics
        total_return = self._calculate_total_return(trades)
        win_rate = self._calculate_win_rate(trades)
        sharpe_ratio = self._calculate_sharpe_ratio(trades)
        max_drawdown = self._calculate_max_drawdown(trades)
        profit_factor = self._calculate_profit_factor(trades)
        avg_win_loss = self._calculate_avg_win_loss(trades)
        total_trades = len([t for t in trades if t.get('side') == 'sell'])
        
        # Time analysis
        days_running = self._days_running(trades)
        trades_per_week = (total_trades / days_running * 7) if days_running > 0 else 0
        
        # Verdict
        verdict = self._get_verdict(total_return, win_rate, sharpe_ratio, max_drawdown)
        
        return {
            'total_return_pct': total_return,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown,
            'profit_factor': profit_factor,
            'avg_win_loss_ratio': avg_win_loss,
            'total_trades': total_trades,
            'days_running': days_running,
            'trades_per_week': trades_per_week,
            'verdict': verdict,
            'last_updated': datetime.now().isoformat()
        }
    
    def _load_trades(self):
        """Load trade history"""
        if not self.trades_file.exists():
            return []
        
        try:
            with open(self.trades_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def _calculate_total_return(self, trades):
        """Total return %"""
        initial_capital = 10000
        
        # Get final equity from last sell trade
        sell_trades = [t for t in trades if t.get('side') == 'sell']
        
        if not sell_trades:
            return 0.0
        
        # Calculate from realized P&L
        total_pnl = sum([t.get('pnl', 0) for t in sell_trades if 'pnl' in t])
        
        return (total_pnl / initial_capital) * 100
    
    def _calculate_win_rate(self, trades):
        """Win rate %"""
        sell_trades = [t for t in trades if t.get('side') == 'sell' and 'pnl' in t]
        
        if not sell_trades:
            return 0.0
        
        wins = len([t for t in sell_trades if t['pnl'] > 0])
        
        return (wins / len(sell_trades)) * 100
    
    def _calculate_sharpe_ratio(self, trades):
        """Sharpe ratio (risk-adjusted returns)"""
        sell_trades = [t for t in trades if t.get('side') == 'sell' and 'pnl' in t]
        
        if len(sell_trades) < 2:
            return 0.0
        
        returns = [t['pnl'] / 10000 for t in sell_trades]  # % returns
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe (assuming ~50 trades/year)
        sharpe = (avg_return / std_return) * np.sqrt(50)
        
        return sharpe
    
    def _calculate_max_drawdown(self, trades):
        """Maximum drawdown %"""
        equity_curve = [10000]  # Start with initial capital
        
        for trade in trades:
            if trade.get('side') == 'sell' and 'pnl' in trade:
                equity_curve.append(equity_curve[-1] + trade['pnl'])
        
        peak = equity_curve[0]
        max_dd = 0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            
            dd = ((peak - equity) / peak) * 100
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def _calculate_profit_factor(self, trades):
        """Profit factor (total wins / total losses)"""
        sell_trades = [t for t in trades if t.get('side') == 'sell' and 'pnl' in t]
        
        if not sell_trades:
            return 0.0
        
        wins = sum([t['pnl'] for t in sell_trades if t['pnl'] > 0])
        losses = abs(sum([t['pnl'] for t in sell_trades if t['pnl'] < 0]))
        
        if losses == 0:
            return float('inf') if wins > 0 else 0.0
        
        return wins / losses
    
    def _calculate_avg_win_loss(self, trades):
        """Average win / average loss ratio"""
        sell_trades = [t for t in trades if t.get('side') == 'sell' and 'pnl' in t]
        
        wins = [t['pnl'] for t in sell_trades if t['pnl'] > 0]
        losses = [abs(t['pnl']) for t in sell_trades if t['pnl'] < 0]
        
        if not wins or not losses:
            return 0.0
        
        avg_win = np.mean(wins)
        avg_loss = np.mean(losses)
        
        return avg_win / avg_loss if avg_loss > 0 else 0.0
    
    def _days_running(self, trades):
        """Days since first trade"""
        if not trades:
            return 0
        
        first_trade = trades[0].get('timestamp')
        if not first_trade:
            return 0
        
        try:
            start = datetime.fromisoformat(first_trade[:19])
            days = (datetime.now() - start).days
            return max(days, 1)
        except:
            return 1
    
    def _get_verdict(self, return_pct, win_rate, sharpe, drawdown):
        """Determine if strategy is working"""
        score = 0
        
        # Return check
        if return_pct > 30:
            score += 3
        elif return_pct > 15:
            score += 2
        elif return_pct > 5:
            score += 1
        
        # Win rate check
        if win_rate > 60:
            score += 2
        elif win_rate > 50:
            score += 1
        
        # Sharpe check
        if sharpe > 2.0:
            score += 2
        elif sharpe > 1.0:
            score += 1
        
        # Drawdown check
        if drawdown < 10:
            score += 2
        elif drawdown < 20:
            score += 1
        
        # Verdict
        if score >= 7:
            return {
                'status': 'EXCELLENT',
                'message': '🎉 Strategy is working great! Keep running!',
                'action': 'Continue with current settings'
            }
        elif score >= 5:
            return {
                'status': 'GOOD',
                'message': '✅ Strategy is profitable. Minor tweaks possible.',
                'action': 'Monitor for another 2 weeks'
            }
        elif score >= 3:
            return {
                'status': 'OKAY',
                'message': '⚠️ Marginal performance. Needs improvement.',
                'action': 'Review losing trades, adjust thresholds'
            }
        else:
            return {
                'status': 'POOR',
                'message': '❌ Strategy not profitable yet.',
                'action': 'Stop trading. Analyze what went wrong.'
            }
    
    def _default_metrics(self):
        """Default metrics when no trades"""
        return {
            'total_return_pct': 0.0,
            'win_rate': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown_pct': 0.0,
            'profit_factor': 0.0,
            'avg_win_loss_ratio': 0.0,
            'total_trades': 0,
            'days_running': 0,
            'trades_per_week': 0.0,
            'verdict': {
                'status': 'INITIALIZING',
                'message': '⏳ Not enough data yet. Need at least 5 trades.',
                'action': 'Keep running. Check back in 1 week.'
            },
            'last_updated': datetime.now().isoformat()
        }