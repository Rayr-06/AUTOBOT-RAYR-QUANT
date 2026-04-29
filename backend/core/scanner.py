"""
Market Scanner
Scans symbols and identifies high-probability setups
"""

import pandas as pd
from typing import List, Dict
from .confluence import ConfluenceScorer


class MarketScanner:
    """Scan multiple symbols for trading opportunities"""
    
    def __init__(self, min_score: float = 72):
        self.scorer = ConfluenceScorer()
        self.min_score = min_score
    
    
    def scan_symbol(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        """Scan a single symbol"""
        try:
            result = self.scorer.calculate_score(data)
            result['symbol'] = symbol
            
            if result['total_score'] >= self.min_score:
                return result
            
            return None
            
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
            return None
    
    
    def scan_multiple(self, symbols_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """Scan multiple symbols"""
        opportunities = []
        
        for symbol, data in symbols_data.items():
            result = self.scan_symbol(symbol, data)
            if result:
                opportunities.append(result)
        
        # Sort by score
        opportunities.sort(key=lambda x: x['total_score'], reverse=True)
        
        return opportunities
