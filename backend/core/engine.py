"""
Trading Engine
Risk management and portfolio tracking
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import json
from pathlib import Path


class RiskManager:
    """Position sizing and risk management"""
    
    def __init__(self, max_risk_per_trade: float = 0.02, max_portfolio_risk: float = 0.06):
        self.max_risk_per_trade = max_risk_per_trade
        self.max_portfolio_risk = max_portfolio_risk
    
    
    def calculate_position_size(self, account_balance: float, entry_price: float, stop_loss: float) -> float:
        """Calculate position size based on risk"""
        risk_per_share = abs(entry_price - stop_loss)
        max_risk_amount = account_balance * self.max_risk_per_trade
        
        position_size = max_risk_amount / risk_per_share if risk_per_share > 0 else 0
        
        return position_size
    
    
    def validate_trade(self, account_balance: float, current_positions: int, position_value: float) -> bool:
        """Validate if trade meets risk criteria"""
        # Check portfolio exposure
        total_exposure = position_value / account_balance
        
        if total_exposure > 0.3:  # Max 30% in single position
            return False
        
        # Check number of positions
        if current_positions >= 5:  # Max 5 concurrent positions
            return False
        
        return True


class Portfolio:
    """Portfolio tracking and performance"""
    
    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.trades = []
        self.trades_file = Path("data/trades/portfolio_trades.json")
        self.trades_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_trades()
    
    
    def log_trade(self, trade: Dict):
        """Log a trade"""
        trade['timestamp'] = datetime.now().isoformat()
        self.trades.append(trade)
        self._save_trades()
    
    
    def get_performance(self) -> Dict:
        """Calculate portfolio performance"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'total_pnl': 0
            }
        
        winning_trades = [t for t in self.trades if t.get('pnl', 0) > 0]
        total_pnl = sum(t.get('pnl', 0) for t in self.trades)
        
        return {
            'total_trades': len(self.trades),
            'win_rate': len(winning_trades) / len(self.trades) * 100,
            'avg_profit': total_pnl / len(self.trades) if self.trades else 0,
            'total_pnl': total_pnl,
            'roi': (total_pnl / self.initial_capital) * 100
        }
    
    
    def _save_trades(self):
        """Save trades to file"""
        with open(self.trades_file, 'w') as f:
            json.dump(self.trades, f, indent=2)
    
    
    def _load_trades(self):
        """Load trades from file"""
        if self.trades_file.exists():
            with open(self.trades_file, 'r') as f:
                self.trades = json.load(f)
