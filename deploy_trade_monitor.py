#!/usr/bin/env python3
"""
Deploy Trade Monitoring System

Real-time monitoring of the current backtest with alerts for trade generation.
"""

import json
import time
import asyncio
from datetime import datetime

def monitor_backtest_with_alerts(project_id: int, backtest_id: str):
    """Monitor backtest with real-time alerts"""
    
    print(f"🚨 DEPLOYING TRADE MONITOR")
    print(f"📊 Project ID: {project_id}")
    print(f"🎯 Backtest ID: {backtest_id}")
    print("=" * 60)
    
    start_time = datetime.now()
    last_progress = 0.0
    stagnation_start = None
    first_trade_time = None
    last_trade_count = 0
    
    print(f"⏰ Monitoring started at: {start_time.strftime('%H:%M:%S')}")
    print(f"📡 Checking backtest status every 60 seconds...")
    
    while True:
        try:
            current_time = datetime.now()
            elapsed_minutes = (current_time - start_time).total_seconds() / 60
            
            # Get backtest status
            backtest_result = quantconnect_read_backtest(project_id, backtest_id)
            
            if not backtest_result:
                print("❌ Failed to get backtest status")
                time.sleep(30)
                continue
            
            # Check completion
            if backtest_result.get('completed', False):
                print("\n🎉 BACKTEST COMPLETED!")
                
                # Get final results
                orders_result = quantconnect_read_backtest_orders(project_id, backtest_id, 0, 1000)
                final_trades = len(orders_result.get('orders', []))
                
                win_rate = backtest_result.get('winRate', 0) or 0
                sharpe_ratio = backtest_result.get('sharpeRatio', 0) or 0
                net_profit = backtest_result.get('netProfit', 0) or 0
                
                print(f"📊 FINAL RESULTS:")
                print(f"   📈 Total Trades: {final_trades}")
                print(f"   🎯 Win Rate: {win_rate:.1%}")
                print(f"   📊 Sharpe Ratio: {sharpe_ratio:.2f}")
                print(f"   💰 Net Profit: ${net_profit:,.2f}")
                print(f"   ⏱️ Duration: {elapsed_minutes:.1f} minutes")
                
                # Final assessment
                if final_trades == 0:
                    print("\n🚨 CRITICAL ALERT: 0 TRADES GENERATED")
                    print("💡 RECOMMENDATION: Algorithm is too conservative")
                    print("   - Lower ML confidence threshold to 0.40-0.45")
                    print("   - Reduce volume anomaly multiplier to 1.25-1.5")
                    print("   - Decrease minimum confluence score to 1-2")
                elif final_trades < 5:
                    print(f"\n⚠️ WARNING: Low trade count ({final_trades})")
                    print("💡 RECOMMENDATION: Further parameter relaxation needed")
                else:
                    print(f"\n✅ SUCCESS: Good trade generation ({final_trades} trades)")
                
                return {
                    'completed': True,
                    'trades': final_trades,
                    'win_rate': win_rate,
                    'sharpe_ratio': sharpe_ratio,
                    'net_profit': net_profit,
                    'duration_minutes': elapsed_minutes
                }
            
            # Get current metrics
            progress = backtest_result.get('progress', 0.0)
            
            # Get trade count
            orders_result = quantconnect_read_backtest_orders(project_id, backtest_id, 0, 1000)
            current_trades = len(orders_result.get('orders', []))
            
            # Calculate metrics
            tradeable_days = backtest_result.get('tradeableDates', 259)
            processed_days = int(progress * tradeable_days)
            trade_rate = current_trades / max(processed_days, 1) if processed_days > 0 else 0
            
            # Check for alerts
            
            # 1. Zero trades after 10 minutes
            if current_trades == 0 and elapsed_minutes >= 10:
                print(f"🚨 [{current_time.strftime('%H:%M:%S')}] ZERO TRADES ALERT")
                print(f"   ⏱️ {elapsed_minutes:.1f} minutes elapsed, 0 trades generated")
                print(f"   📊 Progress: {progress:.1%} ({processed_days} days processed)")
            
            # 2. First trade detection
            if current_trades > 0 and first_trade_time is None:
                first_trade_time = current_time
                print(f"✅ [{current_time.strftime('%H:%M:%S')}] FIRST TRADE DETECTED!")
                print(f"   ⏱️ After {elapsed_minutes:.1f} minutes")
                print(f"   📈 Total trades: {current_trades}")
            
            # 3. New trades detected
            if current_trades > last_trade_count:
                new_trades = current_trades - last_trade_count
                print(f"📈 [{current_time.strftime('%H:%M:%S')}] {new_trades} new trade(s) detected")
                print(f"   📊 Total: {current_trades} | Rate: {trade_rate:.3f} trades/day")
                last_trade_count = current_trades
            
            # 4. Low trade rate after processing some data
            if processed_days > 10 and trade_rate < 0.1:
                print(f"⚠️ [{current_time.strftime('%H:%M:%S')}] LOW TRADE RATE ALERT")
                print(f"   📊 Rate: {trade_rate:.3f} trades/day")
                print(f"   📈 Total trades: {current_trades}")
                print(f"   📅 Processed: {processed_days} days")
            
            # 5. Progress stagnation
            progress_change = progress - last_progress
            if progress_change < 0.02:  # Less than 2% progress
                if stagnation_start is None:
                    stagnation_start = current_time
                elif (current_time - stagnation_start).total_seconds() > 300:  # 5 minutes
                    print(f"⚠️ [{current_time.strftime('%H:%M:%S')}] PROGRESS STAGNATION")
                    print(f"   📊 Stuck at {progress:.1%} for 5+ minutes")
                    stagnation_start = None
            else:
                stagnation_start = None
            
            # Regular status update
            if int(elapsed_minutes) % 5 == 0:  # Every 5 minutes
                print(f"📊 [{current_time.strftime('%H:%M:%S')}] Status Update")
                print(f"   📈 Progress: {progress:.1%} ({processed_days}/{tradeable_days} days)")
                print(f"   📊 Trades: {current_trades} (Rate: {trade_rate:.3f}/day)")
                print(f"   ⏱️ Elapsed: {elapsed_minutes:.1f} minutes")
            
            last_progress = progress
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
            time.sleep(30)

def main():
    """Main deployment"""
    PROJECT_ID = 25780050
    
    # Get the latest backtest (the one in queue)
    print("🔍 Finding latest backtest...")
    backtests_result = quantconnect_list_backtests(PROJECT_ID)
    
    if not backtests_result.get('success'):
        print("❌ Failed to get backtests")
        return
    
    backtests = backtests_result.get('backtests', [])
    
    # Find the most recent backtest
    latest_backtest = None
    for backtest in backtests:
        if backtest.get('status') in ['In Queue...', 'In Progress...']:
            latest_backtest = backtest
            break
    
    if not latest_backtest:
        print("❌ No running backtests found")
        return
    
    backtest_id = latest_backtest['backtestId']
    backtest_name = latest_backtest['name']
    status = latest_backtest['status']
    
    print(f"✅ Found backtest: {backtest_name}")
    print(f"🆔 ID: {backtest_id}")
    print(f"📊 Status: {status}")
    
    # Start monitoring
    print(f"\n🚀 Starting real-time monitoring...")
    result = monitor_backtest_with_alerts(PROJECT_ID, backtest_id)
    
    # Save monitoring report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"trade_monitoring_report_{timestamp}.json"
    
    monitoring_report = {
        'timestamp': datetime.now().isoformat(),
        'project_id': PROJECT_ID,
        'backtest_id': backtest_id,
        'backtest_name': backtest_name,
        'monitoring_results': result
    }
    
    with open(report_file, 'w') as f:
        json.dump(monitoring_report, f, indent=2)
    
    print(f"\n💾 Monitoring report saved to: {report_file}")

if __name__ == "__main__":
    main()