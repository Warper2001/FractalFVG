#!/usr/bin/env python3
"""
Simplified Parameter Optimization for MNQ FVG ML Algorithm

Tests different parameter combinations to address conservative trade generation.
"""

import json
import time
from datetime import datetime

# Import the QuantConnect tools
import sys
sys.path.append('.')

def run_optimization():
    """Run parameter optimization using direct QuantConnect calls"""
    PROJECT_ID = 25780050
    
    print("🚀 Starting MNQ FVG ML Parameter Optimization")
    print("=" * 60)
    
    # Get latest compile
    print("🔧 Compiling algorithm...")
    compile_result = quantconnect_compile_project(PROJECT_ID)
    
    if not compile_result.get('success'):
        print(f"❌ Compilation failed: {compile_result}")
        return
    
    compile_id = compile_result['compileId']
    print(f"✅ Compilation successful: {compile_id}")
    
    # Define parameter combinations to test
    parameter_combinations = [
        {
            'name': 'Aggressive - Low ML Threshold',
            'params': {
                "ml_confidence_threshold": 0.40,
                "volume_anomaly_multiplier": 1.25,
                "min_confluence_score": 2,
                "risk_reward_ratio": 1.5,
                "stop_loss_ticks": 15,
                "take_profit_ticks": 25
            }
        },
        {
            'name': 'Moderate - Balanced Settings',
            'params': {
                "ml_confidence_threshold": 0.45,
                "volume_anomaly_multiplier": 1.5,
                "min_confluence_score": 2,
                "risk_reward_ratio": 2.0,
                "stop_loss_ticks": 20,
                "take_profit_ticks": 40
            }
        },
        {
            'name': 'Conservative+ - Slightly Relaxed',
            'params': {
                "ml_confidence_threshold": 0.50,
                "volume_anomaly_multiplier": 1.75,
                "min_confluence_score": 3,
                "risk_reward_ratio": 2.0,
                "stop_loss_ticks": 20,
                "take_profit_ticks": 40
            }
        }
    ]
    
    print(f"\n🎯 Testing {len(parameter_combinations)} parameter combinations")
    print("=" * 60)
    
    results = []
    
    for i, combo in enumerate(parameter_combinations, 1):
        print(f"\n📍 Combination {i}/{len(parameter_combinations)}: {combo['name']}")
        print(f"📊 Parameters: {json.dumps(combo['params'], indent=2)}")
        
        try:
            # Create backtest with parameters
            backtest_name = f"Optimization - {combo['name']}"
            result = quantconnect_create_backtest(
                project_id=PROJECT_ID,
                compile_id=compile_id,
                backtest_name=backtest_name,
                parameters=combo['params']
            )
            
            if not result.get('success'):
                print(f"❌ Backtest creation failed: {result.get('error', 'Unknown error')}")
                results.append({
                    'combination_name': combo['name'],
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                })
                continue
            
            backtest_id = result['backtestId']
            print(f"✅ Backtest created: {backtest_id}")
            
            # Store for monitoring
            results.append({
                'combination_name': combo['name'],
                'backtest_id': backtest_id,
                'success': True,
                'parameters': combo['params'],
                'start_time': datetime.now().isoformat()
            })
            
            print(f"⏳ Backtest {backtest_id} started. Will monitor completion...")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'combination_name': combo['name'],
                'success': False,
                'error': str(e)
            })
    
    # Monitor all backtests
    print(f"\n⏱️ Monitoring {len([r for r in results if r.get('success')])} backtests...")
    
    successful_results = [r for r in results if r.get('success')]
    
    if not successful_results:
        print("❌ No successful backtests created")
        return
    
    # Wait and check completion
    max_wait_minutes = 30
    start_time = time.time()
    
    while True:
        all_completed = True
        
        for result in successful_results:
            if 'completed' not in result:
                try:
                    backtest_result = quantconnect_read_backtest(PROJECT_ID, result['backtest_id'])
                    
                    if backtest_result.get('completed', False):
                        print(f"✅ Backtest {result['backtest_id']} completed")
                        
                        # Get results
                        orders_result = quantconnect_read_backtest_orders(PROJECT_ID, result['backtest_id'], 0, 1000)
                        trades = len(orders_result.get('orders', []))
                        
                        result.update({
                            'completed': True,
                            'trades': trades,
                            'win_rate': backtest_result.get('winRate', 0),
                            'sharpe_ratio': backtest_result.get('sharpeRatio', 0),
                            'net_profit': backtest_result.get('netProfit', 0),
                            'progress': 1.0
                        })
                        
                        print(f"📈 Results: {trades} trades, Win Rate: {result['win_rate']:.1%}, Sharpe: {result['sharpe_ratio']:.2f}")
                        
                    else:
                        progress = backtest_result.get('progress', 0)
                        result['progress'] = progress
                        all_completed = False
                        
                except Exception as e:
                    print(f"⚠️ Error checking {result['backtest_id']}: {e}")
                    all_completed = False
        
        if all_completed:
            break
        
        # Check timeout
        if time.time() - start_time > max_wait_minutes * 60:
            print(f"⏰ Timeout reached after {max_wait_minutes} minutes")
            break
        
        print(f"⏳ Waiting... (elapsed: {int((time.time() - start_time) / 60)} minutes)")
        time.sleep(120)  # Check every 2 minutes
    
    # Final results analysis
    print("\n" + "=" * 60)
    print("📊 OPTIMIZATION RESULTS SUMMARY")
    print("=" * 60)
    
    completed_results = [r for r in successful_results if r.get('completed')]
    
    if not completed_results:
        print("❌ No backtests completed in time")
        return
    
    # Sort by trades generated
    completed_results.sort(key=lambda x: x.get('trades', 0), reverse=True)
    
    print(f"\n🏆 RESULTS BY TRADE GENERATION:")
    for i, result in enumerate(completed_results, 1):
        print(f"\n{i}. {result['combination_name']}")
        print(f"   📈 Trades: {result.get('trades', 0)}")
        print(f"   🎯 Win Rate: {result.get('win_rate', 0):.1%}")
        print(f"   📊 Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}")
        print(f"   💰 Net Profit: ${result.get('net_profit', 0):,.2f}")
        print(f"   🆔 Backtest ID: {result['backtest_id']}")
    
    # Find best
    best_result = completed_results[0]
    
    print(f"\n🥇 BEST OVERALL COMBINATION:")
    print(f"   Name: {best_result['combination_name']}")
    print(f"   Trades: {best_result.get('trades', 0)}")
    print(f"   Win Rate: {best_result.get('win_rate', 0):.1%}")
    print(f"   Parameters: {json.dumps(best_result['parameters'], indent=6)}")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"parameter_optimization_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'project_id': PROJECT_ID,
            'compile_id': compile_id,
            'total_combinations': len(parameter_combinations),
            'successful_tests': len(successful_results),
            'completed_tests': len(completed_results),
            'best_combination': best_result,
            'all_results': results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if best_result.get('trades', 0) == 0:
        print("⚠️ All combinations still generated 0 trades.")
        print("   Algorithm needs more aggressive parameter tuning.")
    elif best_result.get('trades', 0) < 5:
        print("⚠️ Low trade generation. Consider further optimization.")
    else:
        print("✅ Successful trade generation achieved!")
        print("   Deploy these parameters for production.")

if __name__ == "__main__":
    run_optimization()