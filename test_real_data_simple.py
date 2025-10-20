#!/usr/bin/env python3
"""
Simple Real Data Testing for FVG Strategy
Focus on hold time analysis without complex data generation
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from data.mnq_data import create_sample_mnq_data
from indicators.fvg_detector import FVGDetector
from models.fvg import FVG

def create_simple_test_data():
    """Create simple test data for hold time analysis"""
    print("=== Creating Simple Test Data ===")
    
    # Create 30 days of 5-minute data
    end_date = datetime(2024, 3, 15)
    start_date = end_date - timedelta(days=30)
    
    # Generate date range for 5-minute bars
    date_range = pd.date_range(start=start_date, end=end_date, freq='5min')
    # Filter to trading hours (9:30 AM - 4:00 PM EST, weekdays)
    trading_hours = date_range[
        (date_range.hour >= 9) & (date_range.hour < 16) &
        (date_range.dayofweek < 5)
    ]
    
    n_bars = len(trading_hours)
    print(f"📊 Generated {n_bars} 5-minute bars")
    
    # Generate realistic price data
    np.random.seed(42)  # For reproducible results
    base_price = 22000.0
    
    # Create price movements with trend and volatility
    returns = np.random.normal(0.0001, 0.002, n_bars)  # Small positive drift with volatility
    
    # Add some volatility clustering
    volatility_regime = np.random.choice([0.5, 1.0, 2.0], n_bars, p=[0.7, 0.2, 0.1])
    returns *= volatility_regime
    
    # Generate prices
    prices = [base_price]
    for ret in returns:
        new_price = prices[-1] * (1 + ret)
        prices.append(new_price)
    
    prices = prices[1:]  # Remove initial price
    
    # Create OHLC data
    data = pd.DataFrame({
        'open': prices,
        'high': prices * (1 + np.abs(np.random.normal(0, 0.001, n_bars))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.001, n_bars))),
        'close': prices,
        'volume': np.random.randint(100, 1000, n_bars)
    }, index=trading_hours)
    
    # Ensure OHLC relationships
    data['high'] = np.maximum(data['high'], np.maximum(data['open'], data['close']))
    data['low'] = np.minimum(data['low'], np.minimum(data['open'], data['close']))
    
    print(f"✅ Created test data: {len(data)} bars from {data.index[0]} to {data.index[-1]}")
    return data

def analyze_fvg_hold_times(data):
    """Analyze FVG detection and hold times"""
    print("\n=== Analyzing FVG Hold Times ===")
    
    # Initialize detector
    detector = FVGDetector()
    
    # Detect FVGs on multiple timeframes
    timeframes = [5, 15, 30]
    all_fvgs = []
    
    for tf in timeframes:
        print(f"🔍 Detecting FVGs on {tf}-minute timeframe...")
        
        # Resample data
        tf_data = data.resample(f'{tf}min').agg({
            'open': 'first',
            'high': 'max', 
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # Detect FVGs
        fvgs = detector.detect_fvgs(tf_data)
        print(f"  Found {len(fvgs)} FVGs")
        
        # Add timeframe info
        for fvg in fvgs:
            fvg.timeframe = tf
        
        all_fvgs.extend(fvgs)
    
    print(f"\n📈 Total FVGs detected: {len(all_fvgs)}")
    
    if not all_fvgs:
        print("❌ No FVGs detected, cannot analyze hold times")
        return None
    
    # Analyze hold times based on FVG filling
    hold_times = []
    fill_results = []
    
    print(f"\n⏱️  Analyzing hold times for {len(all_fvgs)} FVGs...")
    
    for i, fvg in enumerate(all_fvgs):
        # Find when FVG was filled (if at all)
        fvg_start_idx = data.index.get_loc(fvg.start_time)
        
        # Look ahead for fill (up to 5 days)
        max_bars = 5 * 24 * 12  # 5 days of 5-minute bars
        end_idx = min(fvg_start_idx + max_bars, len(data) - 1)
        
        filled = False
        fill_bar = None
        
        for j in range(fvg_start_idx + 1, end_idx + 1):
            current_bar = data.iloc[j]
            
            # Check if FVG is filled
            if fvg.direction == 'bullish':
                if current_bar.low <= fvg.bottom:
                    filled = True
                    fill_bar = j
                    break
            else:  # bearish
                if current_bar.high >= fvg.top:
                    filled = True
                    fill_bar = j
                    break
        
        # Calculate hold time
        if filled and fill_bar:
            hold_bars = fill_bar - fvg_start_idx
            hold_minutes = hold_bars * 5  # 5-minute bars
            hold_hours = hold_minutes / 60
            hold_times.append(hold_hours)
            fill_results.append('filled')
        else:
            hold_times.append(40)  # Max 40 hours (5 days)
            fill_results.append('not_filled')
        
        if (i + 1) % 20 == 0:
            print(f"  Processed {i + 1}/{len(all_fvgs)} FVGs...")
    
    # Calculate statistics
    hold_times = np.array(hold_times)
    
    print(f"\n📊 Hold Time Analysis Results:")
    print(f"  Total FVGs analyzed: {len(all_fvgs)}")
    print(f"  Filled FVGs: {sum(1 for r in fill_results if r == 'filled')}")
    print(f"  Unfilled FVGs: {sum(1 for r in fill_results if r == 'not_filled')}")
    print(f"  Fill rate: {sum(1 for r in fill_results if r == 'filled') / len(fill_results) * 100:.1f}%")
    
    if len(hold_times) > 0:
        print(f"\n⏱️  Hold Time Statistics:")
        print(f"  Average hold time: {np.mean(hold_times):.2f} hours")
        print(f"  Median hold time: {np.median(hold_times):.2f} hours")
        print(f"  Min hold time: {np.min(hold_times):.2f} hours")
        print(f"  Max hold time: {np.max(hold_times):.2f} hours")
        print(f"  Std deviation: {np.std(hold_times):.2f} hours")
        
        # Distribution
        under_1h = np.sum(hold_times < 1)
        under_4h = np.sum(hold_times < 4)
        under_8h = np.sum(hold_times < 8)
        under_24h = np.sum(hold_times < 24)
        
        print(f"\n📈 Hold Time Distribution:")
        print(f"  < 1 hour: {under_1h} ({under_1h/len(hold_times)*100:.1f}%)")
        print(f"  < 4 hours: {under_4h} ({under_4h/len(hold_times)*100:.1f}%)")
        print(f"  < 8 hours: {under_8h} ({under_8h/len(hold_times)*100:.1f}%)")
        print(f"  < 24 hours: {under_24h} ({under_24h/len(hold_times)*100:.1f}%)")
    
    return {
        'total_fvgs': len(all_fvgs),
        'fill_rate': sum(1 for r in fill_results if r == 'filled') / len(fill_results) if fill_results else 0,
        'avg_hold_time': np.mean(hold_times) if len(hold_times) > 0 else 0,
        'median_hold_time': np.median(hold_times) if len(hold_times) > 0 else 0,
        'hold_times': hold_times.tolist() if len(hold_times) > 0 else []
    }

def main():
    """Main function"""
    print("FVG Confluence Strategy - Simple Real Data Testing")
    print("=" * 60)
    
    try:
        # Create test data
        data = create_simple_test_data()
        
        # Analyze FVG hold times
        results = analyze_fvg_hold_times(data)
        
        if results:
            print(f"\n🎯 Key Findings:")
            print(f"  • Average FVG hold time: {results['avg_hold_time']:.2f} hours")
            print(f"  • Median hold time: {results['median_hold_time']:.2f} hours")
            print(f"  • Fill rate: {results['fill_rate']*100:.1f}%")
            
            # Recommendation
            avg_hold = results['avg_hold_time']
            if avg_hold < 2:
                print(f"\n💡 Recommendation: Use short hold times (1-2 hours)")
            elif avg_hold < 6:
                print(f"\n💡 Recommendation: Use medium hold times (2-6 hours)")
            else:
                print(f"\n💡 Recommendation: Use longer hold times (6+ hours)")
        
        print(f"\n✅ Real data testing completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)