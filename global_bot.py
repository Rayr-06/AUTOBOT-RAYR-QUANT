"""
GLOBAL ADAPTIVE BOT
Trades multiple markets simultaneously with adaptive strategies
"""
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.brokers.paper import PaperBroker
from backend.core.confluence import ConfluenceScorer
from backend.core.indicators import calculate_all_indicators
from backend.core.regime import RegimeDetector
from backend.core.kelly import KellyPositionSizer
from backend.services.universal_data import UniversalDataProvider
from config_markets import get_all_tradeable_symbols, get_capital_allocation

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("GlobalBot")

class GlobalBot:
    def __init__(self, initial_capital=10000):
        self.symbols = get_all_tradeable_symbols()
        self.broker = PaperBroker(initial_capital=initial_capital)
        self.scorer = ConfluenceScorer()
        self.regime_detector = RegimeDetector()
        self.kelly_sizer = KellyPositionSizer(max_kelly_fraction=0.5)
        self.data_provider = UniversalDataProvider()
        
        self.strategies = {
            'AGGRESSIVE': {'entry': 65, 'exit': 45, 'max_pos': 4},
            'BALANCED': {'entry': 72, 'exit': 50, 'max_pos': 3},
            'CONSERVATIVE': {'entry': 80, 'exit': 60, 'max_pos': 2}
        }
        
        log.info("="*80)
        log.info(f"GLOBAL BOT INITIALIZED - Trading {len(self.symbols)} symbols")
        log.info("="*80)
    
    def analyze_symbol(self, symbol):
        """Analyze a symbol"""
        try:
            df = self.data_provider.get_data(symbol, period=50)
            
            if df.empty or len(df) < 30:
                return None
            
            df = calculate_all_indicators(df)
            score_result = self.scorer.calculate_score(df)
            regime_result = self.regime_detector.detect(df)
            current_price = float(df['close'].iloc[-1])
            
            return {
                'symbol': symbol,
                'price': current_price,
                'score': score_result['total_score'],
                'signal': score_result['signal'],
                'regime': regime_result['regime'],
                'best_strategy': regime_result['best_strategy'],
                'volatility': regime_result['volatility']
            }
            
        except Exception as e:
            log.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def run(self):
        try:
            log.info("\n" + "="*80)
            log.info("GLOBAL BOT SCAN STARTED")
            log.info("="*80 + "\n")
            
            # Analyze all symbols
            analyses = []
            log.info(f"Scanning {len(self.symbols)} symbols...\n")
            
            for symbol in self.symbols:
                result = self.analyze_symbol(symbol)
                if result:
                    analyses.append(result)
                    log.info(f"{symbol:15s} | Score: {result['score']:5.1f} | {result['regime']:12s} | ${result['price']:>10,.2f}")
            
            log.info(f"\n✓ Analyzed {len(analyses)} symbols successfully\n")
            
            # Check exits
            self.check_exits()
            
            # Check entries - trade top opportunities
            self.check_entries(analyses)
            
            # Save results
            self.save_results(analyses)
            
            balance = self.broker.get_balance()
            log.info("\n" + "="*80)
            log.info("SCAN COMPLETE")
            log.info(f"Equity: ${balance['total_equity']:,.2f} | P&L: ${balance['pnl']:,.2f} ({balance['pnl_pct']:+.2f}%)")
            log.info("="*80 + "\n")
            
        except Exception as e:
            log.error(f"Bot error: {e}", exc_info=True)
    
    def check_exits(self):
        """Check all positions for exits"""
        positions = self.broker.get_positions()
        
        if not positions:
            return
        
        log.info("Checking exits for open positions...\n")
        
        for pos in positions:
            result = self.analyze_symbol(pos['symbol'])
            
            if not result:
                continue
            
            # Determine exit threshold based on regime
            regime_map = {
                'TRENDING': 45,
                'CHOPPY': 50,
                'VOLATILE': 60
            }
            exit_threshold = regime_map.get(result['regime'], 50)
            
            if result['score'] < exit_threshold:
                log.info(f"EXIT: {pos['symbol']}")
                log.info(f"  Score: {result['score']:.1f} < {exit_threshold}")
                log.info(f"  P&L: ${pos['unrealized_pnl']:,.2f} ({pos['unrealized_pnl_pct']:+.2f}%)\n")
                
                self.broker.execute_order(pos['symbol'], "sell", pos['qty'])
    
    def check_entries(self, analyses):
        """Check for new entries"""
        positions = self.broker.get_positions()
        balance = self.broker.get_balance()
        
        # Filter opportunities
        opportunities = []
        
        for analysis in analyses:
            # Determine entry threshold based on regime
            regime_map = {
                'TRENDING': 65,
                'CHOPPY': 72,
                'VOLATILE': 80
            }
            entry_threshold = regime_map.get(analysis['regime'], 72)
            
            # Skip if not above threshold
            if analysis['score'] < entry_threshold:
                continue
            
            # Skip if already have position
            if any(p['symbol'] == analysis['symbol'] for p in positions):
                continue
            
            opportunities.append({
                **analysis,
                'entry_threshold': entry_threshold
            })
        
        if not opportunities:
            log.info("No entry opportunities found\n")
            return
        
        # Sort by score (best first)
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        log.info(f"\nFound {len(opportunities)} opportunities:")
        for opp in opportunities[:5]:  # Show top 5
            log.info(f"  {opp['symbol']:15s} | Score: {opp['score']:5.1f} | Entry: {opp['entry_threshold']}")
        
        # Trade top opportunities (max 8 total positions)
        max_total_positions = 8
        trades = self.broker.get_trade_history()
        stats = self.kelly_sizer.get_historical_stats(trades)
        
        for opp in opportunities:
            if len(self.broker.get_positions()) >= max_total_positions:
                break
            
            symbol = opp['symbol']
            price = opp['price']
            
            # Calculate position size
            capital_allocation = get_capital_allocation(symbol)
            available_capital = balance['total_equity'] * capital_allocation
            
            kelly_risk = self.kelly_sizer.calculate_size(
                stats['win_rate'],
                stats['avg_win'],
                stats['avg_loss'],
                available_capital
            )
            
            stop_distance = price * 0.02
            qty = kelly_risk / stop_distance
            qty = round(qty, 6)
            
            if qty > 0:
                log.info(f"\nENTRY: {symbol}")
                log.info(f"  Score: {opp['score']:.1f}")
                log.info(f"  Regime: {opp['regime']}")
                log.info(f"  Price: ${price:,.2f}")
                log.info(f"  Qty: {qty:.6f}\n")
                
                self.broker.execute_order(symbol, "buy", qty)
    
    def save_results(self, analyses):
        """Save results"""
        balance = self.broker.get_balance()
        positions = self.broker.get_positions()
        
        # Top scores for dashboard
        scores = {}
        for analysis in sorted(analyses, key=lambda x: x['score'], reverse=True)[:10]:
            scores[analysis['symbol']] = {
                'score': analysis['score'],
                'signal': analysis['signal'],
                'price': analysis['price'],
                'regime': analysis['regime']
            }
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'total_symbols_scanned': len(analyses),
            'bot': {
                'running': True,
                'last_run': datetime.now().isoformat()
            },
            'account': {
                'equity': balance['total_equity'],
                'cash': balance['balance'],
                'positions_value': balance['positions_value'],
                'pnl': balance['pnl'],
                'pnl_pct': balance['pnl_pct']
            },
            'positions': positions,
            'top_scores': scores
        }
        
        Path("data").mkdir(exist_ok=True)
        with open("data/status.json", "w") as f:
            json.dump(status, f, indent=2)

if __name__ == "__main__":
    bot = GlobalBot(initial_capital=10000)
    bot.run()