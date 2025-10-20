#!/usr/bin/env python3
"""
Demonstration of 1-minute resolution performance metrics

This script shows how to use the enhanced performance metrics
with 1-minute resolution analysis for FVG trading strategy.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backtesting_performance_metrics import PerformanceMetrics, FuturesMetricsConfig


def create_sample_intraday_data():
    """Create sample 1-minute resolution data for demonstration"""
    
    # Create 1-minute data for 3 trading days
    minutes_per_day = 390  # 6.5 hours * 60 minutes
    total_minutes = minutes_per_day * 3
    
    # Create datetime index for trading hours (9:30 AM - 4:00 PM)
    start_date = datetime(2024, 1, 1, 9, 30)
    dates = []
    for day in range(3):
        for minute in range(minutes_per_day):
            dates.append(start_date + timedelta(days=day, minutes=minute))
    
    dates = pd.DatetimeIndex(dates)
    
    # Create realistic intraday returns with FVG-inspired patterns
    np.random.seed(42)
    
    # Base returns with slight upward drift
    base_returns = np.random.normal(0.00005, 0.0015, total_minutes)
    
    # Add intraday patterns typical of FVG trading
    for i, date in enumerate(dates):
        hour = date.hour
        minute = date.minute
        
        # Market open volatility (FVG opportunities)
        if hour == 9 and minute >= 30 and minute < 45:
            base_returns[i] *= 3.0  # Higher volatility at open
            if np.random.random() > 0.7:  # 30% chance of gap
                base_returns[i] += np.random.choice([-0.003, 0.003])
        
        # Mid-day consolidation (lower FVG activity)
        elif hour == 12:
            base_returns[i] *= 0.5  # Lower volatility
        
        # Market close volatility (FVG opportunities)
        elif hour == 15 and minute >= 30:
            base_returns[i] *= 2.5  # Higher volatility at close
    
    returns = pd.Series(base_returns, index=dates)
    
    # Create equity curve
    equity_curve = (1 + returns).cumprod() * 100000  # Start with $100k
    
    return returns, equity_curve


def demonstrate_intraday_metrics():
    """Demonstrate the 1-minute resolution metrics functionality"""
    
    print("=" * 60)
    print("1-MINUTE RESOLUTION PERFORMANCE METRICS DEMONSTRATION")
    print("=" * 60)
    
    # Create sample data
    print("\n1. Creating sample 1-minute resolution data...")
    returns, equity_curve = create_sample_intraday_data()
    print(f"   - Total minutes: {len(returns):,}")
    print(f"   - Date range: {returns.index[0]} to {returns.index[-1]}")
    print(f"   - Starting equity: ${equity_curve.iloc[0]:,.2f}")
    print(f"   - Ending equity: ${equity_curve.iloc[-1]:,.2f}")
    print(f"   - Total return: {(equity_curve.iloc[-1]/equity_curve.iloc[0] - 1):.2%}")
    
    # Initialize metrics with 1-minute analysis enabled
    print("\n2. Initializing performance metrics with 1-minute resolution...")
    config = FuturesMetricsConfig(
        enable_intraday_analysis=True,
        minutes_per_trading_day=390
    )
    metrics = PerformanceMetrics(config)
    print("   ✓ Intraday analysis enabled")
    print("   ✓ 390 minutes per trading day configured")
    
    # Calculate high-frequency metrics
    print("\n3. Calculating high-frequency metrics...")
    hf_metrics = metrics.high_frequency_metrics(returns)
    
    print(f"   - Total minutes analyzed: {hf_metrics['total_minutes']:,}")
    print(f"   - Positive minutes: {hf_metrics['positive_minutes']:,} ({hf_metrics['positive_minutes']/hf_metrics['total_minutes']:.1%})")
    print(f"   - Negative minutes: {hf_metrics['negative_minutes']:,} ({hf_metrics['negative_minutes']/hf_metrics['total_minutes']:.1%})")
    print(f"   - Max minute gain: {hf_metrics['max_minute_gain']:.6f}")
    print(f"   - Max minute loss: {hf_metrics['max_minute_loss']:.6f}")
    print(f"   - Max consecutive positive minutes: {hf_metrics['max_consecutive_positive_minutes']}")
    print(f"   - Max consecutive negative minutes: {hf_metrics['max_consecutive_negative_minutes']}")
    
    # Time of day analysis
    print("\n4. Analyzing performance by time of day...")
    time_analysis = metrics.time_of_day_analysis(returns)
    
    if "best_performing_time" in time_analysis:
        best = time_analysis["best_performing_time"]
        print(f"   - Best performing time: {best['time']}")
        print(f"     Sharpe ratio: {best['sharpe']:.3f}")
        print(f"     Mean return: {best['mean_return']:.6f}")
    
    if "worst_performing_time" in time_analysis:
        worst = time_analysis["worst_performing_time"]
        print(f"   - Worst performing time: {worst['time']}")
        print(f"     Sharpe ratio: {worst['sharpe']:.3f}")
        print(f"     Mean return: {worst['mean_return']:.6f}")
    
    # Session analysis
    print("\n5. Analyzing performance by trading session...")
    session_analysis = metrics.session_analysis(returns)
    
    if "session_metrics" in session_analysis:
        for session, sess_metrics in session_analysis["session_metrics"].items():
            print(f"   - {session.replace('_', ' ').title()}:")
            print(f"     Annual return: {sess_metrics['annual_return']:.2%}")
            print(f"     Sharpe ratio: {sess_metrics['sharpe']:.3f}")
            print(f"     Win rate: {sess_metrics['win_rate']:.2%}")
            print(f"     Volatility: {sess_metrics['volatility']:.2%}")
    
    # Rolling metrics
    print("\n6. Calculating rolling intraday metrics...")
    rolling_vol = metrics.intraday_volatility(returns, 60)
    rolling_sharpe = metrics.intraday_sharpe_ratio(returns, 60)
    
    print(f"   - 60-minute rolling volatility (latest): {rolling_vol.iloc[-1]:.2%}")
    print(f"   - 60-minute rolling Sharpe ratio (latest): {rolling_sharpe.iloc[-1]:.3f}")
    print(f"   - Average rolling volatility: {rolling_vol.mean():.2%}")
    print(f"   - Average rolling Sharpe ratio: {rolling_sharpe.mean():.3f}")
    
    # Comprehensive analysis
    print("\n7. Running comprehensive analysis with 1-minute metrics...")
    analysis = metrics.comprehensive_analysis(equity_curve)
    
    # Standard performance metrics
    perf = analysis["performance_metrics"]
    print(f"   - Annual return: {perf['annual_return']:.2%}")
    print(f"   - Sharpe ratio: {perf['sharpe_ratio']:.3f}")
    print(f"   - Maximum drawdown: {perf['maximum_drawdown']:.2%}")
    print(f"   - Win rate: {perf['win_rate']:.2%}")
    print(f"   - Profit factor: {perf['profit_factor']:.2f}")
    
    # Verify intraday metrics are included
    if "intraday_metrics" in analysis:
        print("   ✓ 1-minute resolution metrics included in analysis")
        intraday = analysis["intraday_metrics"]
        print(f"   - High-frequency metrics: {len(intraday['high_frequency'])} items")
        print(f"   - Time-of-day analysis: {len(intraday['time_of_day'])} items")
        print(f"   - Session analysis: {len(intraday['session_analysis'])} items")
    else:
        print("   ✗ 1-minute resolution metrics NOT found")
    
    # Generate report
    print("\n8. Generating performance report...")
    report = metrics.generate_report(analysis)
    
    # Save report to file
    report_path = "intraday_performance_report.txt"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"   ✓ Report saved to: {report_path}")
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("\nThe enhanced performance metrics now include:")
    print("• 1-minute resolution volatility and Sharpe ratio calculations")
    print("• Time-of-day performance analysis")
    print("• Trading session performance breakdown")
    print("• High-frequency statistics and streak analysis")
    print("• Rolling intraday drawdown calculations")
    print("• Comprehensive visualization with intraday focus")
    print(f"\nView the detailed report in: {report_path}")


if __name__ == "__main__":
    demonstrate_intraday_metrics()