"""
MASTER ADAPTIVE BOT
Selects best strategy based on market regime
Uses Kelly Criterion for position sizing
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
from backend.services.data_provider import DataProvider

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("MasterBot")

class MasterBot:
    def __init__(self):
        self.symbols = ["BTC-USD", "ETH-USD"]
        self.broker = PaperBroker(initial_capital=10000)
        self.scorer = ConfluenceScorer()
        self.regime_detector = RegimeDetector()
        self.kelly_sizer = KellyPositionSizer(max_kelly_fraction=0.5)
        self.data_provider = DataProvider()
        
        # Strategy parameters based on regime
        self.strategies = {
            'AGGRESSIVE': {
                'entry_score': 65,
                'exit_score': 45,
                'base_risk': 0.03,
                'max_positions': 4
            },
            'BALANCED': {
                'entry_score': 72,
                'exit_score': 50,
                'base_risk': 0.02,
                'max_positions': 3
            },
            'CONSERVATIVE': {
                'entry_score': 80,
                'exit_score': 60,
                'base_risk': 0.01,
                'max_positions': 2
            }
        }
        
        log.info("="*80)
        log.info("MASTER ADAPTIVE BOT - INITIALIZED")
        log.info("="*80)
    
    def analyze_symbol(self, symbol):
        """Full analysis with regime detection"""
        try:
            df = self.data_provider.get_ohlcv(symbol, 50)
            
            if df.empty or len(df) < 30:
                return None
            
            df = calculate_all_indicators(df)
            
            # Confluence score
            score_result = self.scorer.calculate_score(df)
            
            # Market regime
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
            log.info("STARTING BOT RUN")
            log.info("="*80 + "\n")
            
            # Analyze all symbols
            analyses = []
            for symbol in self.symbols:
                result = self.analyze_symbol(symbol)
                if result:
                    analyses.append(result)
                    log.info(f"{symbol}:")
                    log.info(f"  Score: {result['score']:.1f}")
                    log.info(f"  Regime: {result['regime']}")
                    log.info(f"  Strategy: {result['best_strategy']}")
                    log.info(f"  Price: ${result['price']:,.2f}\n")
            
            # Determine dominant regime
            if analyses:
                regimes = [a['regime'] for a in analyses]
                dominant_regime = max(set(regimes), key=regimes.count)
                
                # Map regime to strategy
                regime_to_strategy = {
                    'TRENDING': 'AGGRESSIVE',
                    'CHOPPY': 'BALANCED',
                    'VOLATILE': 'CONSERVATIVE'
                }
                
                current_strategy = regime_to_strategy.get(dominant_regime, 'BALANCED')
                params = self.strategies[current_strategy]
                
                log.info("="*80)
                log.info(f"MARKET REGIME: {dominant_regime}")
                log.info(f"SELECTED STRATEGY: {current_strategy}")
                log.info(f"Entry: {params['entry_score']}+ | Exit: <{params['exit_score']}")
                log.info("="*80 + "\n")
                
                # Check exits first
                self.check_exits(params)
                
                # Check entries
                self.check_entries(analyses, params)
                
                # Save results
                self.save_results(current_strategy, analyses)
            
            log.info("\n" + "="*80)
            log.info("BOT RUN COMPLETE")
            
            balance = self.broker.get_balance()
            log.info(f"Equity: ${balance['total_equity']:,.2f}")
            log.info(f"P&L: ${balance['pnl']:,.2f} ({balance['pnl_pct']:+.2f}%)")
            log.info("="*80 + "\n")
            
        except Exception as e:
            log.error(f"Bot error: {e}", exc_info=True)
    
    def check_exits(self, params):
        """Check if any positions should be exited"""
        for pos in self.broker.get_positions():
            result = self.analyze_symbol(pos['symbol'])
            
            if result and result['score'] < params['exit_score']:
                log.info(f"EXIT SIGNAL: {pos['symbol']}")
                log.info(f"  Score dropped to {result['score']:.1f} (< {params['exit_score']})")
                log.info(f"  P&L: ${pos['unrealized_pnl']:,.2f} ({pos['unrealized_pnl_pct']:+.2f}%)\n")
                
                self.broker.execute_order(pos['symbol'], "sell", pos['qty'])
    
    def check_entries(self, analyses, params):
        """Check for new entry signals"""
        positions = self.broker.get_positions()
        balance = self.broker.get_balance()
        
        # Get historical stats for Kelly
        trades = self.broker.get_trade_history()
        stats = self.kelly_sizer.get_historical_stats(trades)
        
        for analysis in analyses:
            symbol = analysis['symbol']
            score = analysis['score']
            price = analysis['price']
            
            # Skip if already have position
            if any(p['symbol'] == symbol for p in positions):
                continue
            
            # Skip if max positions reached
            if len(positions) >= params['max_positions']:
                continue
            
            # Check entry signal
            if score >= params['entry_score']:
                # Calculate position size using Kelly
                kelly_risk = self.kelly_sizer.calculate_size(
                    stats['win_rate'],
                    stats['avg_win'],
                    stats['avg_loss'],
                    balance['total_equity']
                )
                
                # ATR-based stop
                stop_distance = price * 0.02  # 2% stop as baseline
                qty = kelly_risk / stop_distance
                qty = round(qty, 6)
                
                if qty > 0:
                    log.info(f"ENTRY SIGNAL: {symbol}")
                    log.info(f"  Score: {score:.1f} (>= {params['entry_score']})")
                    log.info(f"  Price: ${price:,.2f}")
                    log.info(f"  Kelly Risk: ${kelly_risk:,.2f}")
                    log.info(f"  Quantity: {qty:.6f}\n")
                    
                    self.broker.execute_order(symbol, "buy", qty)
    
    def save_results(self, strategy, analyses):
        """Save results for dashboard"""
        balance = self.broker.get_balance()
        positions = self.broker.get_positions()
        
        # Build scores dict
        scores = {}
        for analysis in analyses:
            scores[analysis['symbol']] = {
                'score': analysis['score'],
                'signal': analysis['signal'],
                'price': analysis['price'],
                'regime': analysis['regime']
            }
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'strategy': strategy,
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
            'scores': scores
        }
        
        Path("data").mkdir(exist_ok=True)
        with open("data/status.json", "w") as f:
            json.dump(status, f, indent=2)
        
        log.info("Status saved to data/status.json")

if __name__ == "__main__":
    bot = MasterBot()
    bot.run()