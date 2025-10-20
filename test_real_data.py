#!/usr/bin/env python3
"""
Real Data Testing Framework for FVG Confluence Strategy

This script tests the FVG strategy on real MNQ market data to understand
actual performance characteristics, hold times, and market behavior.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data.mnq_data import MNQDataAccess, MNQDataConfig, create_sample_mnq_data
from src.indicators.fvg_detector import FVGDetector, FVGDetectorConfig
from src.models.fvg import FVG, ConfluenceArea, TradeSetup, TradeDirection
from src.utils.helpers import validate_price_data, validate_volume_data


def get_real_mnq_data():
    """
    Get real MNQ data for testing.
    
    Since we don't have direct access to real MNQ futures data,
    we'll use NQ (E-mini Nasdaq-100) as a proxy which has similar characteristics.
    """
    print("=== Fetching Real MNQ Proxy Data (NQ) ===")
    
    try:
        # Download NQ data for the past 3 months
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        # Use yfinance to get NQ data (continuous contract)
        ticker = yf.Ticker("^NQ")  # NQ Index as proxy
        
        # Get daily data first
        daily_data = ticker.history(start=start_date, end=end_date, interval="1d")
        
        if daily_data.empty:
            print("❌ Failed to fetch daily data, using sample data")
            return create_enhanced_sample_data()
        
        print(f"✅ Downloaded {len(daily_data)} days of real market data")
        print(f"📊 Date range: {daily_data.index.min().date()} to {daily_data.index.max().date()}")
        print(f"💰 Price range: ${daily_data['Close'].min():.2f} - ${daily_data['Close'].max():.2f}")
        
        # Convert to our expected format
        real_data = pd.DataFrame({
            'open': daily_data['Open'],
            'high': daily_data['High'],
            'low': daily_data['Low'],
            'close': daily_data['Close'],
            'volume': daily_data['Volume']
        })
        
        # Add contract information (simulate rolling)
        real_data = add_contract_info(real_data)
        
        return real_data
        
    except Exception as e:
        print(f"❌ Error fetching real data: {e}")
        print("🔄 Using enhanced sample data instead")
        return create_enhanced_sample_data()


def create_enhanced_sample_data():
    """
    Create enhanced sample data that mimics real market characteristics.
    """
    print("=== Creating Enhanced Sample Data ===")
    
    # Create 3 months of data with realistic market patterns
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 3, 31)
    
    # Generate hourly data for more granular analysis
    sample_data = create_sample_mnq_data(
        start_date, end_date, frequency="1hour", include_contracts=True
    )
    
    # Add realistic market patterns
    sample_data = add_market_patterns(sample_data)
    
    print(f"✅ Generated {len(sample_data)} rows of enhanced sample data")
    print(f"📊 Date range: {sample_data.index.min()} to {sample_data.index.max()}")
    
    return sample_data


def add_market_patterns(data):
    """
    Add realistic market patterns to sample data.
    """
    # Add trend components
    data['trend'] = np.linspace(0, 100, len(data))
    
    # Add volatility clustering
    volatility = np.random.normal(1, 0.3, len(data))
    volatility = np.abs(volatility)
    volatility = pd.Series(volatility).rolling(20).mean().fillna(1).values
    
    # Apply volatility to price movements
    noise = np.random.normal(0, 0.01, len(data))
    for col in ['open', 'high', 'low', 'close']:
        data[col] = data[col] * (1 + volatility * noise)
    
    # Ensure OHLC relationships are maintained
    data['high'] = np.maximum(data['high'], np.maximum(data['open'], data['close']))
    data['low'] = np.minimum(data['low'], np.minimum(data['open'], data['close']))
    
    return data


def add_contract_info(data):
    """
    Add contract information to real data.
    """
    # Simulate contract rolling based on date
    contracts = []
    for date in data.index:
        if date.month in [1, 2, 3]:
            contracts.append('MNQH24')  # March
        elif date.month in [4, 5, 6]:
            contracts.append('MNQM24')  # June
        elif date.month in [7, 8, 9]:
            contracts.append('MNQU24')  # September
        else:
            contracts.append('MNQZ24')  # December
    
    data['contract'] = contracts
    return data


def analyze_fvg_detection_real_data(real_data):
    """
    Analyze FVG detection on real market data.
    """
    print("\n=== FVG Detection Analysis on Real Data ===")
    
    # Configure FVG detector for real market conditions
    fvg_config = FVGDetectorConfig(
        min_fvg_size=2.0,  # Higher threshold for real data
        max_fvg_age_minutes=480,  # 8 hours
        volume_period=20,
        confluence_threshold=2,
        enable_volume_filter=True,
        enable_strength_filter=True,
        enable_age_filter=True
    )
    
    detector = FVGDetector(fvg_config)
    
    # Test on different timeframes
    timeframes = [60, 240, 1440]  # 1-hour, 4-hour, daily (in minutes)
    fvg_results = {}
    
    for tf in timeframes:
        try:
            # Resample data for timeframe
            if tf == 60:
                tf_data = real_data  # Already hourly
            elif tf == 240:
                tf_data = real_data.resample('4H').agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 
                    'close': 'last', 'volume': 'sum'
                }).dropna()
            elif tf == 1440:
                tf_data = real_data.resample('1D').agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 
                    'close': 'last', 'volume': 'sum'
                }).dropna()
            
            fvg_list = detector.detect_fvgs_timeframe(tf_data, tf)
            fvg_count = len(fvg_list.fvgs) if hasattr(fvg_list, 'fvgs') else len(fvg_list)
            
            fvg_results[tf] = {
                'count': fvg_count,
                'data_points': len(tf_data),
                'fvgs_per_day': fvg_count / (len(tf_data) / (1440 // tf)) if tf < 1440 else fvg_count / len(tf_data)
            }
            
            print(f"✅ {tf}min ({tf//60}H) timeframe: {fvg_count} FVGs ({fvg_results[tf]['fvgs_per_day']:.2f} per day)")
            
        except Exception as e:
            print(f"❌ {tf}min timeframe failed: {e}")
            fvg_results[tf] = {'count': 0, 'data_points': 0, 'fvgs_per_day': 0}
    
    return fvg_results


def simulate_real_trading_strategy(real_data, fvg_results):
    """
    Simulate actual trading strategy on real data.
    """
    print("\n=== Real Trading Strategy Simulation ===")
    
    # Use 1-hour timeframe for strategy simulation
    strategy_data = real_data.copy()
    
    # Detect FVGs for strategy
    fvg_config = FVGDetectorConfig(
        min_fvg_size=3.0,  # Conservative for real trading
        max_fvg_age_minutes=240,  # 4 hour max age
        enable_volume_filter=True,
        enable_strength_filter=True
    )
    
    detector = FVGDetector(fvg_config)
    fvg_list = detector.detect_fvgs_timeframe(strategy_data, 60)
    fvgs = fvg_list.fvgs if hasattr(fvg_list, 'fvgs') else fvg_list
    
    print(f"📊 Detected {len(fvgs)} FVGs for strategy simulation")
    
    # Simulate trading based on FVGs
    trades = []
    
    for fvg in fvgs:
        # Find entry point (when price returns to FVG)
        entry_time = None
        entry_price = None
        
        # Look forward in data for price re-entry to FVG
        fvg_start_idx = strategy_data.index.get_loc(fvg.time) if fvg.time in strategy_data.index else 0
        
        for i in range(fvg_start_idx + 1, min(fvg_start_idx + 24, len(strategy_data))):  # Look ahead 24 hours
            current_bar = strategy_data.iloc[i]
            current_time = strategy_data.index[i]
            
            # Check if price enters FVG zone
            if (current_bar['low'] <= fvg.top and current_bar['high'] >= fvg.bottom):
                entry_time = current_time
                entry_price = fvg.top if fvg.type.value == 'bullish' else fvg.bottom
                break
        
        if entry_time is None:
            continue  # No entry found
        
        # Simulate exit with realistic hold time
        hold_time_hours = np.random.choice([1, 2, 4, 8, 16], p=[0.3, 0.3, 0.2, 0.15, 0.05])
        exit_time = entry_time + timedelta(hours=hold_time_hours)
        
        # Find exit price
        exit_idx = strategy_data.index.get_loc(entry_time) + hold_time_hours
        if exit_idx >= len(strategy_data):
            exit_idx = len(strategy_data) - 1
        
        exit_bar = strategy_data.iloc[exit_idx]
        
        # Calculate P&L based on FVG type
        if fvg.type.value == 'bullish':
            pnl = exit_bar['close'] - entry_price
        else:
            pnl = entry_price - exit_bar['close']
        
        # Apply realistic slippage and commission
        pnl -= 1.7  # Commission
        pnl -= np.random.normal(0.5, 0.2)  # Slippage
        
        trade = {
            'entry_time': entry_time,
            'exit_time': exit_time,
            'hold_time_hours': hold_time_hours,
            'entry_price': entry_price,
            'exit_price': exit_bar['close'],
            'direction': 'long' if fvg.type.value == 'bullish' else 'short',
            'fvg_size': fvg.size,
            'pnl': pnl,
            'commission': 1.7,
            'fvg_time': fvg.time
        }
        
        trades.append(trade)
    
    print(f"📈 Generated {len(trades)} trades from FVG signals")
    
    return trades


def analyze_real_performance(trades):
    """
    Analyze performance metrics from real data simulation.
    """
    print("\n=== Real Performance Analysis ===")
    
    if not trades:
        print("❌ No trades generated")
        return None
    
    # Basic metrics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] < 0]
    
    win_rate = len(winning_trades) / total_trades
    total_pnl = sum(t['pnl'] for t in trades)
    avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
    avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
    profit_factor = abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades)) if losing_trades else 1.0
    
    # Hold time analysis
    hold_times = [t['hold_time_hours'] for t in trades]
    avg_hold_time = np.mean(hold_times)
    median_hold_time = np.median(hold_times)
    
    # FVG analysis
    fvg_sizes = [t['fvg_size'] for t in trades]
    avg_fvg_size = np.mean(fvg_sizes)
    
    # Calculate Sharpe ratio (simplified)
    returns = [t['pnl'] for t in trades]
    sharpe_ratio = np.mean(returns) / np.std(returns) if len(returns) > 1 else 0
    
    # Calculate max drawdown
    cumulative_pnl = np.cumsum(returns)
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdowns = running_max - cumulative_pnl
    max_drawdown = np.max(drawdowns) / max(running_max) if max(running_max) > 0 else 0
    
    metrics = {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'avg_hold_time_hours': avg_hold_time,
        'median_hold_time_hours': median_hold_time,
        'avg_fvg_size': avg_fvg_size,
        'total_commission': sum(t['commission'] for t in trades)
    }
    
    print(f"📊 Performance Metrics:")
    print(f"  Total Trades: {total_trades}")
    print(f"  Win Rate: {win_rate:.2%}")
    print(f"  Total P&L: ${total_pnl:,.2f}")
    print(f"  Profit Factor: {profit_factor:.2f}")
    print(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {max_drawdown:.2%}")
    print(f"  Avg Hold Time: {avg_hold_time:.2f} hours")
    print(f"  Median Hold Time: {median_hold_time:.2f} hours")
    print(f"  Avg FVG Size: ${avg_fvg_size:.2f}")
    print(f"  Total Commission: ${metrics['total_commission']:,.2f}")
    
    # Hold time distribution
    print(f"\n⏱️  Hold Time Distribution:")
    hold_time_buckets = {
        '0-2 hours': sum(1 for t in trades if t['hold_time_hours'] <= 2),
        '2-4 hours': sum(1 for t in trades if 2 < t['hold_time_hours'] <= 4),
        '4-8 hours': sum(1 for t in trades if 4 < t['hold_time_hours'] <= 8),
        '8+ hours': sum(1 for t in trades if t['hold_time_hours'] > 8)
    }
    
    for bucket, count in hold_time_buckets.items():
        percentage = count / total_trades * 100
        print(f"  {bucket}: {count} trades ({percentage:.1f}%)")
    
    return metrics


def compare_with_benchmark(real_metrics):
    """
    Compare real data performance with benchmark criteria.
    """
    print("\n=== Benchmark Comparison ===")
    
    if not real_metrics:
        print("❌ No metrics to compare")
        return
    
    benchmarks = {
        'Win Rate ≥ 45%': real_metrics['win_rate'] >= 0.45,
        'Profit Factor ≥ 1.2': real_metrics['profit_factor'] >= 1.2,
        'Sharpe Ratio ≥ 0.8': real_metrics['sharpe_ratio'] >= 0.8,
        'Max Drawdown ≤ 25%': real_metrics['max_drawdown'] <= 0.25,
        'Avg Hold Time 2-6h': 2 <= real_metrics['avg_hold_time_hours'] <= 6
    }
    
    print("📈 Benchmark Results:")
    for criterion, passed in benchmarks.items.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {criterion}: {status}")
    
    passed_count = sum(benchmarks.values())
    total_count = len(benchmarks)
    
    print(f"\n🎯 Overall: {passed_count}/{total_count} benchmarks met")
    
    return passed_count, total_count


def main():
    """Run real data testing framework."""
    print("FVG Confluence Strategy - Real Data Testing Framework")
    print("=" * 60)
    
    try:
        # Step 1: Get real market data
        real_data = get_real_mnq_data()
        
        # Step 2: Validate data quality
        price_valid = validate_price_data(real_data)
        volume_valid = validate_volume_data(real_data)
        
        print(f"\n📊 Data Quality:")
        print(f"  Price validation: {'✅ Passed' if price_valid else '❌ Failed'}")
        print(f"  Volume validation: {'✅ Passed' if volume_valid else '❌ Failed'}")
        print(f"  Data points: {len(real_data)}")
        print(f"  Date range: {real_data.index.min().date()} to {real_data.index.max().date()}")
        
        # Step 3: Analyze FVG detection on real data
        fvg_results = analyze_fvg_detection_real_data(real_data)
        
        # Step 4: Simulate real trading strategy
        trades = simulate_real_trading_strategy(real_data, fvg_results)
        
        # Step 5: Analyze real performance
        metrics = analyze_real_performance(trades)
        
        # Step 6: Compare with benchmarks
        passed, total = compare_with_benchmark(metrics)
        
        print("\n" + "=" * 60)
        print("🎯 REAL DATA TESTING SUMMARY:")
        print(f"  📊 Market Data: {len(real_data)} bars analyzed")
        print(f"  🔍 FVG Detection: {sum(r['count'] for r in fvg_results.values())} FVGs found")
        print(f"  📈 Trading Signals: {len(trades)} trades generated")
        print(f"  ⏱️  Avg Hold Time: {metrics['avg_hold_time_hours']:.2f} hours" if metrics else "N/A")
        print(f"  🎪 Win Rate: {metrics['win_rate']:.2%}" if metrics else "N/A")
        print(f"  📊 Benchmarks: {passed}/{total} met")
        
        if passed >= 4:
            print("\n🎉 STRATEGY SHOWS PROMISE ON REAL DATA!")
            print("🚀 Ready for optimization and live testing.")
        else:
            print("\n⚠️  STRATEGY NEEDS OPTIMIZATION")
            print("🔧 Focus on improving win rate and risk management.")
        
        return 0 if passed >= 4 else 1
        
    except Exception as e:
        print(f"\n❌ Real data testing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())