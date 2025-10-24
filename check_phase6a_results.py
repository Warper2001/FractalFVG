#!/usr/bin/env python3
"""
Check Phase 6A backtest results using working API v2
"""

import requests
import base64
import time
import hashlib
import json

# Configuration
USER_ID = "421529"
API_TOKEN = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
PROJECT_ID = 25780050
BASE_URL = "https://www.quantconnect.com/api/v2"

def get_headers():
    """Generate proper authentication headers with timestamp"""
    timestamp = f'{int(time.time())}'
    time_stamped_token = f'{API_TOKEN}:{timestamp}'.encode('utf-8')
    
    # Get hashed API token
    hashed_token = hashlib.sha256(time_stamped_token).hexdigest()
    authentication = f'{USER_ID}:{hashed_token}'.encode('utf-8')
    authentication = base64.b64encode(authentication).decode('ascii')
    
    return {
        'Authorization': f'Basic {authentication}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }

def check_backtest_results():
    """Check Phase 6A backtest results"""
    print("📊 Checking Phase 6A Backtest Results")
    print("=" * 50)
    
    # Get backtest results
    print("📋 Getting backtest results...")
    backtest_data = {'projectId': PROJECT_ID}
    backtest_response = requests.post(f"{BASE_URL}/backtests/read", headers=get_headers(), json=backtest_data)
    
    if backtest_response.status_code != 200:
        print(f"❌ Failed to get backtest results: {backtest_response.status_code}")
        return False
    
    backtest_result = backtest_response.json()
    if not backtest_result.get('success'):
        print(f"❌ API returned error: {backtest_result}")
        return False
    
    backtest = backtest_result.get('backtest', {})
    if not backtest:
        print("❌ No backtest data found")
        return False
    
    print(f"✅ Found backtest: {backtest.get('name', 'Unknown')}")
    print(f"🆔 Backtest ID: {backtest.get('backtestId', 'Unknown')}")
    print(f"📊 Status: {backtest.get('status', 'Unknown')}")
    print(f"✅ Completed: {backtest.get('completed', False)}")
    print(f"📅 Created: {backtest.get('created', 'Unknown')}")
    print(f"⏰ Started: {backtest.get('backtestStart', 'Unknown')}")
    print(f"🏁 Ended: {backtest.get('backtestEnd', 'Unknown')}")
    print(f"📈 Progress: {backtest.get('progress', 0)}%")
    
    # Check for errors
    error = backtest.get('error')
    if error:
        print(f"❌ Error: {error}")
        return False
    
    # Get runtime statistics
    runtime_stats = backtest.get('runtimeStatistics', {})
    if runtime_stats:
        print(f"\n📈 Runtime Statistics:")
        print(f"  • Equity: {runtime_stats.get('Equity', 'N/A')}")
        print(f"  • Net Profit: {runtime_stats.get('Net Profit', 'N/A')}")
        print(f"  • Return: {runtime_stats.get('Return', 'N/A')}")
        print(f"  • Sharpe Ratio: {runtime_stats.get('Probabilistic Sharpe Ratio', 'N/A')}")
        print(f"  • Fees: {runtime_stats.get('Fees', 'N/A')}")
        print(f"  • Holdings: {runtime_stats.get('Holdings', 'N/A')}")
        print(f"  • Volume: {runtime_stats.get('Volume', 'N/A')}")
    
    # Get trade statistics
    total_perf = backtest.get('totalPerformance', {})
    trade_stats = total_perf.get('tradeStatistics', {})
    if trade_stats:
        print(f"\n💼 Trade Statistics:")
        print(f"  • Total Trades: {trade_stats.get('totalNumberOfTrades', 0)}")
        print(f"  • Winning Trades: {trade_stats.get('numberOfWinningTrades', 0)}")
        print(f"  • Losing Trades: {trade_stats.get('numberOfLosingTrades', 0)}")
        print(f"  • Win Rate: {trade_stats.get('winRate', '0%')}")
        print(f"  • Total Profit/Loss: {trade_stats.get('totalProfitLoss', '0')}")
        print(f"  • Largest Profit: {trade_stats.get('largestProfit', '0')}")
        print(f"  • Largest Loss: {trade_stats.get('largestLoss', '0')}")
        print(f"  • Average Trade: {trade_stats.get('averageProfitLoss', '0')}")
        print(f"  • Sharpe Ratio: {trade_stats.get('sharpeRatio', '0')}")
        print(f"  • Sortino Ratio: {trade_stats.get('sortinoRatio', '0')}")
        print(f"  • Profit Factor: {trade_stats.get('profitFactor', '0')}")
        print(f"  • Max Drawdown: {trade_stats.get('maximumClosedTradeDrawdown', '0')}")
    
    # Get portfolio statistics
    portfolio_stats = total_perf.get('portfolioStatistics', {})
    if portfolio_stats:
        print(f"\n💰 Portfolio Statistics:")
        print(f"  • Start Equity: {portfolio_stats.get('startEquity', '0')}")
        print(f"  • End Equity: {portfolio_stats.get('endEquity', '0')}")
        print(f"  • Total Net Profit: {portfolio_stats.get('totalNetProfit', '0')}")
        print(f"  • Compounding Annual Return: {portfolio_stats.get('compoundingAnnualReturn', '0')}")
        print(f"  • Drawdown: {portfolio_stats.get('drawdown', '0')}")
        print(f"  • Alpha: {portfolio_stats.get('alpha', '0')}")
        print(f"  • Beta: {portfolio_stats.get('beta', '0')}")
        print(f"  • Information Ratio: {portfolio_stats.get('informationRatio', '0')}")
        print(f"  • Treynor Ratio: {portfolio_stats.get('treynorRatio', '0')}")
        print(f"  • VaR 99%: {portfolio_stats.get('valueAtRisk99', '0')}")
        print(f"  • VaR 95%: {portfolio_stats.get('valueAtRisk95', '0')}")
    
    # Check Phase 6A specific success metrics
    print(f"\n🎯 Phase 6A Analysis:")
    tradeable_dates = backtest.get('tradeableDates', 0)
    total_trades = trade_stats.get('totalNumberOfTrades', 0)
    
    if tradeable_dates > 0:
        print(f"  ✅ Tradeable Dates: {tradeable_dates}")
        print(f"  🎉 SUCCESS: Direct MNQH24 contract is working!")
    else:
        print(f"  ⚠️  Tradeable Dates: {tradeable_dates}")
        print(f"  ❌ May still have data access issues")
    
    if total_trades > 0:
        print(f"  ✅ Total Trades: {total_trades}")
        print(f"  🎉 SUCCESS: Phase 6A algorithm is executing trades!")
        print(f"  🚀 The direct contract solution SOLVED the execution issue!")
    else:
        print(f"  ⚠️  Total Trades: {total_trades}")
        print(f"  ❌ Algorithm may need further optimization")
    
    # Check if completed and save results
    if backtest.get('completed', False):
        print(f"\n🎉 Backtest COMPLETED successfully!")
        
        # Save detailed results
        results_file = f"phase6a_results_{backtest.get('backtestId', 'unknown')}.json"
        with open(results_file, 'w') as f:
            json.dump(backtest_result, f, indent=2)
        print(f"💾 Detailed results saved to: {results_file}")
        
        return True
    else:
        status = backtest.get('status', 'Unknown')
        print(f"\n⏳ Backtest still running... Status: {status}")
        print(f"🔄 Progress: {backtest.get('progress', 0)}%")
        return False

if __name__ == "__main__":
    check_backtest_results()