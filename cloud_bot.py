"""
AUTOBOT RAYR QUANT - Cloud Bot
Runs on GitHub Actions every hour
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
from backend.services.data_provider import DataProvider

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger("CloudBot")

class CloudBot:
    def __init__(self):
        self.symbols = ["BTC-USD", "ETH-USD"]
        self.broker = PaperBroker(initial_capital=10000)
        self.scorer = ConfluenceScorer()
        self.data_provider = DataProvider()
        self.min_score = 72
        self.max_positions = 3
        self.risk_per_trade = 0.02
        
        log.info("="*80)
        log.info("AUTOBOT RAYR QUANT - Cloud Run")
        log.info("="*80)
    
    def analyze_symbol(self, symbol):
        try:
            log.info(f"Analyzing {symbol}...")
            df = self.data_provider.get_ohlcv(symbol, 50)
            
            if df.empty or len(df) < 30:
                return None
            
            df = calculate_all_indicators(df)
            result = self.scorer.calculate_score(df)
            result['symbol'] = symbol
            result['current_price'] = float(df['close'].iloc[-1])
            
            log.info(f"{symbol}: Score={result['total_score']:.1f} Signal={result['signal']} Price=${result['current_price']:,.2f}")
            
            return result
        except Exception as e:
            log.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def execute_trade(self, symbol, signal):
        try:
            entry = signal['current_price']
            stop = entry * 0.98
            balance = self.broker.get_balance()['total_equity']
            risk = balance * self.risk_per_trade
            qty = risk / abs(entry - stop) if abs(entry - stop) > 0 else 0
            qty = min(qty, balance * 0.1 / entry)
            qty = round(qty, 6)
            
            if qty <= 0:
                return
            
            log.info("="*80)
            log.info(f"EXECUTING TRADE: BUY {symbol}")
            log.info(f"Score: {signal['total_score']:.1f} | Entry: ${entry:,.2f} | Qty: {qty}")
            
            result = self.broker.execute_order(symbol, "buy", qty)
            
            if result['ok']:
                log.info(f"✅ TRADE EXECUTED! Balance: ${result['balance']:,.2f}")
                log.info("="*80)
                
                # Save trade to log
                self.save_trade_log({
                    'timestamp': datetime.now().isoformat(),
                    'symbol': symbol,
                    'action': 'BUY',
                    'price': entry,
                    'quantity': qty,
                    'score': signal['total_score']
                })
        except Exception as e:
            log.error(f"Error executing trade: {e}")
    
    def check_exits(self):
        for pos in self.broker.get_positions():
            signal = self.analyze_symbol(pos['symbol'])
            
            if signal and signal['total_score'] < 50:
                log.info(f"EXIT SIGNAL: {pos['symbol']} (Score: {signal['total_score']:.1f})")
                
                result = self.broker.execute_order(pos['symbol'], "sell", pos['qty'])
                
                if result['ok']:
                    log.info(f"✅ POSITION CLOSED: P&L ${pos['unrealized_pnl']:,.2f} ({pos['unrealized_pnl_pct']:+.2f}%)")
                    
                    self.save_trade_log({
                        'timestamp': datetime.now().isoformat(),
                        'symbol': pos['symbol'],
                        'action': 'SELL',
                        'price': signal['current_price'],
                        'quantity': pos['qty'],
                        'pnl': pos['unrealized_pnl']
                    })
    
    def save_trade_log(self, trade_data):
        log_file = Path("data/cloud_trades.json")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if log_file.exists():
                with open(log_file, 'r') as f:
                    trades = json.load(f)
            else:
                trades = []
            
            trades.append(trade_data)
            
            with open(log_file, 'w') as f:
                json.dump(trades, f, indent=2)
        except Exception as e:
            log.error(f"Error saving trade log: {e}")
    
    def save_status(self):
        """Save current status for dashboard"""
        status_file = Path("data/status.json")
        status_file.parent.mkdir(parents=True, exist_ok=True)
        
        balance = self.broker.get_balance()
        positions = self.broker.get_positions()
        
        # Get latest scores
        scores = {}
        for symbol in self.symbols:
            signal = self.analyze_symbol(symbol)
            if signal:
                scores[symbol] = {
                    'score': signal['total_score'],
                    'signal': signal['signal'],
                    'price': signal['current_price']
                }
        
        status = {
            'timestamp': datetime.now().isoformat(),
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
        
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)
        
        log.info("Status saved to data/status.json")
    
    def run(self):
        try:
            log.info("Starting cloud bot run...")
            
            # Check exits first
            self.check_exits()
            
            # Scan symbols
            for symbol in self.symbols:
                signal = self.analyze_symbol(symbol)
                
                if signal:
                    positions = self.broker.get_positions()
                    
                    # Check if should trade
                    if (signal['total_score'] >= self.min_score and
                        not any(p['symbol'] == symbol for p in positions) and
                        len(positions) < self.max_positions):
                        
                        self.execute_trade(symbol, signal)
            
            # Save status
            self.save_status()
            
            # Print summary
            balance = self.broker.get_balance()
            log.info("")
            log.info("="*80)
            log.info("RUN COMPLETE")
            log.info(f"Equity: ${balance['total_equity']:,.2f} | P&L: ${balance['pnl']:,.2f} ({balance['pnl_pct']:+.2f}%)")
            log.info("="*80)
            
        except Exception as e:
            log.error(f"Cloud bot error: {e}", exc_info=True)

if __name__ == "__main__":
    bot = CloudBot()
    bot.run()