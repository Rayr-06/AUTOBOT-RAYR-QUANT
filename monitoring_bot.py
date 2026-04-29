"""
COMPLETE MONITORING BOT
Tracks all strategies, all markets, publishes detailed data
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger("MonitorBot")

class MonitoringBot:
    def __init__(self):
        # Define markets
        self.markets = {
            'INDIAN_STOCKS': ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ITC.NS'],
            'US_STOCKS': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'],
            'CRYPTO': ['BTC-USD', 'ETH-USD', 'SOL-USD'],
            'INDICES': ['^NSEI', '^GSPC']
        }
        
        self.strategies = {
            'AGGRESSIVE': {'entry': 65, 'exit': 45, 'color': '🔴'},
            'BALANCED': {'entry': 72, 'exit': 50, 'color': '🟡'},
            'CONSERVATIVE': {'entry': 80, 'exit': 60, 'color': '🟢'}
        }
        
        self.broker = PaperBroker(initial_capital=10000)
        self.scorer = ConfluenceScorer()
        self.regime_detector = RegimeDetector()
        self.kelly_sizer = KellyPositionSizer()
        self.data_provider = DataProvider()
        
        log.info("="*100)
        log.info("MONITORING BOT INITIALIZED")
        log.info("="*100)
    
    def run(self):
        """Run complete monitoring scan"""
        try:
            scan_results = {
                'timestamp': datetime.now().isoformat(),
                'markets': {},
                'strategy_breakdown': {
                    'AGGRESSIVE': {'signals': [], 'count': 0},
                    'BALANCED': {'signals': [], 'count': 0},
                    'CONSERVATIVE': {'signals': [], 'count': 0}
                },
                'live_prices': {},
                'activity_log': []
            }
            
            log.info("\n" + "="*100)
            log.info("MARKET SCAN STARTED")
            log.info("="*100 + "\n")
            
            # Scan each market
            for market_name, symbols in self.markets.items():
                log.info(f"\n{'='*100}")
                log.info(f"SCANNING: {market_name}")
                log.info(f"{'='*100}\n")
                
                market_data = []
                
                for symbol in symbols:
                    result = self.analyze_symbol(symbol)
                    
                    if result:
                        market_data.append(result)
                        
                        # Log to console
                        log.info(f"{symbol:15s} | Price: ${result['price']:>12,.2f} | Score: {result['score']:>6.1f} | {result['regime']:12s} | Best: {result['best_strategy']}")
                        
                        # Store live price
                        scan_results['live_prices'][symbol] = {
                            'price': result['price'],
                            'change_pct': 0.0,  # Calculate if you have historical data
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # Add to activity log
                        scan_results['activity_log'].append({
                            'timestamp': datetime.now().isoformat(),
                            'symbol': symbol,
                            'market': market_name,
                            'price': result['price'],
                            'score': result['score'],
                            'regime': result['regime'],
                            'signal': result['signal']
                        })
                        
                        # Categorize by strategy
                        for strategy_name, params in self.strategies.items():
                            if result['score'] >= params['entry']:
                                scan_results['strategy_breakdown'][strategy_name]['signals'].append({
                                    'symbol': symbol,
                                    'score': result['score'],
                                    'price': result['price'],
                                    'market': market_name
                                })
                                scan_results['strategy_breakdown'][strategy_name]['count'] += 1
                
                scan_results['markets'][market_name] = market_data
                log.info(f"\n✓ Scanned {len(market_data)} symbols in {market_name}\n")
            
            # Save detailed results
            self.save_monitoring_data(scan_results)
            
            # Print summary
            self.print_summary(scan_results)
            
            # Execute trades based on best opportunities
            self.execute_trades(scan_results)
            
        except Exception as e:
            log.error(f"Monitoring error: {e}", exc_info=True)
    
    def analyze_symbol(self, symbol):
        """Analyze a single symbol"""
        try:
            df = self.data_provider.get_ohlcv(symbol, 50)
            
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
    
    def print_summary(self, scan_results):
        """Print detailed summary"""
        log.info("\n" + "="*100)
        log.info("SCAN SUMMARY")
        log.info("="*100 + "\n")
        
        total_symbols = sum(len(data) for data in scan_results['markets'].values())
        log.info(f"📊 Total symbols scanned: {total_symbols}")
        
        log.info("\n📈 STRATEGY BREAKDOWN:")
        for strategy_name, data in scan_results['strategy_breakdown'].items():
            emoji = self.strategies[strategy_name]['color']
            entry = self.strategies[strategy_name]['entry']
            log.info(f"  {emoji} {strategy_name:15s} (Entry: {entry}+): {data['count']} signals")
            
            if data['signals']:
                for signal in data['signals'][:3]:  # Show top 3
                    log.info(f"     - {signal['symbol']:15s} Score: {signal['score']:.1f} | ${signal['price']:,.2f}")
        
        log.info("\n" + "="*100 + "\n")
    
    def execute_trades(self, scan_results):
        """Execute trades based on signals"""
        # Get all signals across strategies
        all_signals = []
        
        for strategy_name, data in scan_results['strategy_breakdown'].items():
            for signal in data['signals']:
                all_signals.append({
                    **signal,
                    'strategy': strategy_name
                })
        
        # Sort by score (best first)
        all_signals.sort(key=lambda x: x['score'], reverse=True)
        
        if not all_signals:
            log.info("No trade signals found\n")
            return
        
        log.info(f"Found {len(all_signals)} total signals")
        log.info("\nTop opportunities:")
        for sig in all_signals[:5]:
            log.info(f"  {sig['symbol']:15s} | {sig['strategy']:15s} | Score: {sig['score']:.1f}")
        
        # Trade top 3 if conditions met
        positions = self.broker.get_positions()
        
        for signal in all_signals[:3]:
            if len(positions) >= 8:  # Max 8 positions
                break
            
            if any(p['symbol'] == signal['symbol'] for p in positions):
                continue
            
            # Execute trade
            log.info(f"\n🎯 EXECUTING: {signal['symbol']} ({signal['strategy']})")
            
            balance = self.broker.get_balance()
            trades = self.broker.get_trade_history()
            stats = self.kelly_sizer.get_historical_stats(trades)
            
            kelly_risk = self.kelly_sizer.calculate_size(
                stats['win_rate'],
                stats['avg_win'],
                stats['avg_loss'],
                balance['total_equity'] * 0.25  # 25% per trade max
            )
            
            qty = kelly_risk / (signal['price'] * 0.02)
            qty = round(qty, 6)
            
            if qty > 0:
                self.broker.execute_order(signal['symbol'], "buy", qty)
                log.info(f"  ✅ Bought {qty} @ ${signal['price']:,.2f}")
    
    def save_monitoring_data(self, scan_results):
        """Save all monitoring data"""
        Path("data").mkdir(exist_ok=True)
        
        # Save full scan results
        with open("data/monitoring.json", "w") as f:
            json.dump(scan_results, f, indent=2)
        
        # Save simplified status for dashboard
        balance = self.broker.get_balance()
        positions = self.broker.get_positions()
        
        # Top scores for dashboard
        top_scores = {}
        for market_data in scan_results['markets'].values():
            for item in market_data:
                top_scores[item['symbol']] = {
                    'score': item['score'],
                    'price': item['price'],
                    'signal': item['signal'],
                    'regime': item['regime']
                }
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'bot': {'running': True, 'last_run': datetime.now().isoformat()},
            'account': {
                'equity': balance['total_equity'],
                'cash': balance['balance'],
                'positions_value': balance['positions_value'],
                'pnl': balance['pnl'],
                'pnl_pct': balance['pnl_pct']
            },
            'positions': positions,
            'scores': top_scores
        }
        
        with open("data/status.json", "w") as f:
            json.dump(status, f, indent=2)
        
        log.info("✓ Monitoring data saved")

if __name__ == "__main__":
    bot = MonitoringBot()
    bot.run()