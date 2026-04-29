"""
RAYR Quant Terminal - Automated Trading Bot
60-Day Paper Trading Validation
"""

import sys
import time
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.brokers.paper import PaperBroker
from backend.core.confluence import ConfluenceScorer
from backend.core.indicators import calculate_all_indicators
from backend.services.data_provider import DataProvider
import json

log_file = Path("logs/bot.log")
log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("AutoBot")


class AutoTradingBot:
    
    def __init__(self):
        self.symbols = ["BTC-USD", "ETH-USD"]
        self.check_interval = 3600
        self.broker = PaperBroker(initial_capital=10000)
        self.scorer = ConfluenceScorer()
        self.data_provider = DataProvider()
        self.min_score = 72
        self.max_positions = 3
        self.risk_per_trade = 0.02
        self.last_signals = {}
        self.trade_count = 0
        self.start_time = datetime.now()
        
        log.info("="*80)
        log.info("RAYR QUANT TERMINAL - 60-DAY VALIDATION")
        log.info("="*80)
        log.info(f"Symbols: {self.symbols}")
        log.info(f"Check Interval: 60 minutes")
        log.info(f"Initial Capital: $10,000")
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
            log.error(f"Error: {e}")
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
            log.info(f"TRADE #{self.trade_count + 1}: BUY {symbol}")
            log.info(f"Score: {signal['total_score']:.1f} | Entry: ${entry:,.2f} | Qty: {qty}")
            
            result = self.broker.execute_order(symbol, "buy", qty)
            if result['ok']:
                self.trade_count += 1
                log.info(f"SUCCESS! Balance: ${result['balance']:,.2f}")
                log.info("="*80)
        except Exception as e:
            log.error(f"Error: {e}")
    
    def check_exits(self):
        for pos in self.broker.get_positions():
            signal = self.analyze_symbol(pos['symbol'])
            if signal and signal['total_score'] < 50:
                log.info(f"EXIT {pos['symbol']} (Score: {signal['total_score']:.1f})")
                result = self.broker.execute_order(pos['symbol'], "sell", pos['qty'])
                if result['ok']:
                    log.info(f"P&L: ${pos['unrealized_pnl']:,.2f} ({pos['unrealized_pnl_pct']:+.2f}%)")
    
    def print_status(self):
        bal = self.broker.get_balance()
        pos = self.broker.get_positions()
        runtime = datetime.now() - self.start_time
        
        log.info("")
        log.info("="*80)
        log.info("STATUS")
        log.info(f"Runtime: {runtime.days}d {runtime.seconds//3600}h | Trades: {self.trade_count}")
        log.info(f"Equity: ${bal['total_equity']:,.2f} | P&L: ${bal['pnl']:,.2f} ({bal['pnl_pct']:+.2f}%)")
        log.info(f"Positions: {len(pos)}")
        for p in pos:
            log.info(f"  {p['symbol']}: {p['qty']:.6f} @ ${p['avg_price']:,.2f} | P&L: ${p['unrealized_pnl']:,.2f}")
        log.info("="*80)
    
    def run(self):
        try:
            log.info("BOT STARTED - Press Ctrl+C to stop\n")
            cycle = 0
            while True:
                cycle += 1
                log.info(f"\n--- CYCLE #{cycle} ---")
                self.check_exits()
                for symbol in self.symbols:
                    signal = self.analyze_symbol(symbol)
                    if signal:
                        self.last_signals[symbol] = signal
                        positions = self.broker.get_positions()
                        if (signal['total_score'] >= self.min_score and
                            not any(p['symbol'] == symbol for p in positions) and
                            len(positions) < self.max_positions and
                            self.last_signals.get(symbol, {}).get('signal') != 'BUY'):
                            self.execute_trade(symbol, signal)
                self.print_status()
                log.info(f"Sleeping 60 minutes...")
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            log.info("\n\nBOT STOPPED")
            self.print_status()


if __name__ == "__main__":
    bot = AutoTradingBot()
    bot.run()