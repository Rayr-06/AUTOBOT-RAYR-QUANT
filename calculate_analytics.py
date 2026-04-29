"""
Analytics Runner
Calculates and saves performance metrics
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.analytics.performance import PerformanceAnalyzer

def main():
    print("\n" + "="*80)
    print("PERFORMANCE ANALYTICS")
    print("="*80 + "\n")
    
    analyzer = PerformanceAnalyzer()
    metrics = analyzer.get_all_metrics()
    
    # Print metrics
    print(f"📊 PERFORMANCE METRICS:")
    print(f"  Total Return:      {metrics['total_return_pct']:>6.2f}%")
    print(f"  Win Rate:          {metrics['win_rate']:>6.2f}%")
    print(f"  Sharpe Ratio:      {metrics['sharpe_ratio']:>6.2f}")
    print(f"  Max Drawdown:      {metrics['max_drawdown_pct']:>6.2f}%")
    print(f"  Profit Factor:     {metrics['profit_factor']:>6.2f}")
    print(f"  Avg Win/Loss:      {metrics['avg_win_loss_ratio']:>6.2f}")
    print(f"  Total Trades:      {metrics['total_trades']:>6}")
    print(f"  Days Running:      {metrics['days_running']:>6}")
    print(f"  Trades/Week:       {metrics['trades_per_week']:>6.1f}")
    
    print(f"\n📋 VERDICT: {metrics['verdict']['status']}")
    print(f"  {metrics['verdict']['message']}")
    print(f"  Action: {metrics['verdict']['action']}")
    
    # Save to file
    Path("data").mkdir(exist_ok=True)
    with open("data/analytics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    print(f"\n✓ Analytics saved to data/analytics.json")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()