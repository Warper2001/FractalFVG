#!/usr/bin/env python3
"""
Performance Regression Analysis

Analyze historical backtest data to detect performance trends and regressions.
"""

import json
from datetime import datetime

def analyze_historical_performance():
    """Analyze historical backtest performance"""
    
    PROJECT_ID = 25780050
    
    print("📊 PERFORMANCE REGRESSION ANALYSIS")
    print("=" * 60)
    
    # Get all backtests
    print("🔍 Retrieving historical backtest data...")
    backtests_result = quantconnect_list_backtests(PROJECT_ID)
    
    if not backtests_result.get('success'):
        print("❌ Failed to retrieve backtests")
        return
    
    backtests = backtests_result.get('backtests', [])
    
    # Filter completed backtests
    completed_backtests = [b for b in backtests if b.get('completed', False)]
    
    print(f"✅ Found {len(completed_backtests)} completed backtests")
    
    if not completed_backtests:
        print("❌ No completed backtests to analyze")
        return
    
    # Analyze each backtest
    performance_data = []
    
    for i, backtest in enumerate(completed_backtests, 1):
        backtest_id = backtest['backtestId']
        name = backtest['name']
        created = backtest['created']
        
        print(f"\n📈 {i}. Analyzing: {name}")
        print(f"🆔 ID: {backtest_id}")
        print(f"📅 Created: {created}")
        
        try:
            # Get detailed results
            orders_result = quantconnect_read_backtest_orders(PROJECT_ID, backtest_id, 0, 1000)
            trades = len(orders_result.get('orders', []))
            
            # Get backtest statistics
            backtest_result = quantconnect_read_backtest(PROJECT_ID, backtest_id)
            
            performance = {
                'backtest_id': backtest_id,
                'name': name,
                'created': created,
                'trades': trades,
                'win_rate': backtest_result.get('winRate', 0) or 0,
                'sharpe_ratio': backtest_result.get('sharpeRatio', 0) or 0,
                'net_profit': backtest_result.get('netProfit', 0) or 0,
                'max_drawdown': backtest_result.get('drawdown', 0) or 0,
                'sortino_ratio': backtest_result.get('sortinoRatio', 0) or 0,
                'alpha': backtest_result.get('alpha', 0) or 0,
                'beta': backtest_result.get('beta', 0) or 0
            }
            
            performance_data.append(performance)
            
            print(f"   📊 Trades: {trades}")
            print(f"   🎯 Win Rate: {performance['win_rate']:.1%}")
            print(f"   📈 Sharpe: {performance['sharpe_ratio']:.2f}")
            print(f"   💰 Profit: ${performance['net_profit']:,.2f}")
            
        except Exception as e:
            print(f"   ❌ Error analyzing: {e}")
            continue
    
    # Performance analysis
    print(f"\n" + "=" * 60)
    print("📊 PERFORMANCE ANALYSIS SUMMARY")
    print("=" * 60)
    
    if not performance_data:
        print("❌ No performance data available")
        return
    
    # Sort by creation time
    performance_data.sort(key=lambda x: x['created'])
    
    # Calculate statistics
    total_trades = sum(p['trades'] for p in performance_data)
    avg_trades = total_trades / len(performance_data)
    
    non_zero_trades = [p for p in performance_data if p['trades'] > 0]
    zero_trade_backtests = len(performance_data) - len(non_zero_trades)
    
    print(f"📈 OVERALL STATISTICS:")
    print(f"   📊 Total Backtests: {len(performance_data)}")
    print(f"   📈 Total Trades: {total_trades}")
    print(f"   📊 Average Trades: {avg_trades:.1f}")
    print(f"   ⚠️ Zero-Trade Backtests: {zero_trade_backtests} ({zero_trade_backtests/len(performance_data)*100:.1f}%)")
    
    if non_zero_trades:
        avg_win_rate = sum(p['win_rate'] for p in non_zero_trades) / len(non_zero_trades)
        avg_sharpe = sum(p['sharpe_ratio'] for p in non_zero_trades) / len(non_zero_trades)
        total_profit = sum(p['net_profit'] for p in non_zero_trades)
        
        print(f"   🎯 Average Win Rate: {avg_win_rate:.1%}")
        print(f"   📊 Average Sharpe: {avg_sharpe:.2f}")
        print(f"   💰 Total Profit: ${total_profit:,.2f}")
    
    # Trend analysis
    print(f"\n📈 TREND ANALYSIS:")
    
    # Trade generation trend
    recent_backtests = performance_data[-3:]  # Last 3 backtests
    if len(recent_backtests) >= 2:
        recent_avg_trades = sum(p['trades'] for p in recent_backtests) / len(recent_backtests)
        older_backtests = performance_data[:-3] if len(performance_data) > 3 else performance_data[:-1]
        
        if older_backtests:
            older_avg_trades = sum(p['trades'] for p in older_backtests) / len(older_backtests)
            
            if recent_avg_trades > older_avg_trades:
                print(f"   ✅ Trade Generation: IMPROVING ({recent_avg_trades:.1f} vs {older_avg_trades:.1f})")
            elif recent_avg_trades < older_avg_trades:
                print(f"   ⚠️ Trade Generation: DECLINING ({recent_avg_trades:.1f} vs {older_avg_trades:.1f})")
            else:
                print(f"   ➡️ Trade Generation: STABLE ({recent_avg_trades:.1f})")
    
    # Performance regression detection
    print(f"\n🚨 REGRESSION DETECTION:")
    
    # Check for zero-trade pattern
    if zero_trade_backtests >= 2:
        print(f"   🚨 CRITICAL: Consistent zero-trade pattern detected")
        print(f"   💡 RECOMMENDATION: Algorithm parameters too conservative")
        print(f"      - Lower ML confidence threshold to 0.40-0.45")
        print(f"      - Reduce volume anomaly multiplier to 1.25-1.5")
        print(f"      - Decrease minimum confluence score to 1-2")
    
    # Check recent performance
    if len(recent_backtests) >= 2:
        recent_trades = [p['trades'] for p in recent_backtests]
        if all(t == 0 for t in recent_trades):
            print(f"   🚨 CRITICAL: Last {len(recent_backtests)} backtests generated 0 trades")
            print(f"   💡 IMMEDIATE ACTION REQUIRED: Parameter optimization needed")
    
    # Best performing backtest
    if non_zero_trades:
        best_backtest = max(non_zero_trades, key=lambda x: x['trades'])
        print(f"\n🏆 BEST PERFORMING BACKTEST:")
        print(f"   📈 Name: {best_backtest['name']}")
        print(f"   📊 Trades: {best_backtest['trades']}")
        print(f"   🎯 Win Rate: {best_backtest['win_rate']:.1%}")
        print(f"   📊 Sharpe: {best_backtest['sharpe_ratio']:.2f}")
        print(f"   💰 Profit: ${best_backtest['net_profit']:,.2f}")
        print(f"   🆔 ID: {best_backtest['backtest_id']}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if zero_trade_backtests > len(performance_data) * 0.5:
        print(f"   🚨 HIGH PRIORITY: Fix conservative algorithm")
        print(f"   📊 Current success rate: {(len(performance_data) - zero_trade_backtests)/len(performance_data)*100:.1f}%")
        print(f"   🔧 Run parameter optimizer with aggressive settings")
    
    if non_zero_trades:
        best_trades = max(p['trades'] for p in non_zero_trades)
        if best_trades < 10:
            print(f"   ⚠️ MEDIUM PRIORITY: Increase trade generation")
            print(f"   📈 Best performance: {best_trades} trades (still low)")
            print(f"   🔧 Fine-tune parameters around best performing backtest")
        else:
            print(f"   ✅ GOOD: Trade generation working")
            print(f"   📈 Best performance: {best_trades} trades")
            print(f"   🔧 Optimize around successful parameters")
    
    # Save analysis
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    analysis_file = f"performance_regression_analysis_{timestamp}.json"
    
    analysis_report = {
        'timestamp': datetime.now().isoformat(),
        'project_id': PROJECT_ID,
        'total_backtests': len(performance_data),
        'performance_data': performance_data,
        'summary': {
            'total_trades': total_trades,
            'average_trades': avg_trades,
            'zero_trade_backtests': zero_trade_backtests,
            'zero_trade_percentage': zero_trade_backtests/len(performance_data)*100
        },
        'recommendations': [
            "Parameter optimization needed for conservative algorithm",
            "Consider lowering ML confidence threshold",
            "Reduce volume anomaly requirements",
            "Monitor trade generation in real-time"
        ]
    }
    
    with open(analysis_file, 'w') as f:
        json.dump(analysis_report, f, indent=2)
    
    print(f"\n💾 Analysis saved to: {analysis_file}")
    
    return analysis_report

def main():
    """Main execution"""
    print("🚀 Starting Performance Regression Analysis")
    
    analysis = analyze_historical_performance()
    
    if analysis:
        print(f"\n✅ Analysis completed successfully")
        print(f"📊 Key finding: {analysis['summary']['zero_trade_percentage']:.1f}% of backtests generated 0 trades")
        
        if analysis['summary']['zero_trade_percentage'] > 50:
            print(f"🚨 CRITICAL: Algorithm optimization required")
        else:
            print(f"✅ Algorithm performance acceptable")

if __name__ == "__main__":
    main()