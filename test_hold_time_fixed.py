#!/usr/bin/env python3
"""
Fixed Hold Time Analysis for FVG Strategy
Creates explicit FVGs to test hold time analysis
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def create_data_with_fvgs():
    """Create price data with explicit FVGs"""
    print("=== Creating Data with Explicit FVGs ===")
    
    # Create 10 days of 5-minute data
    end_date = datetime(2024, 3, 15)
    start_date = end_date - timedelta(days=10)
    
    # Generate trading hours
    trading_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    trading_bars = []
    
    for date in trading_dates:
        if date.weekday() >= 5:  # Skip weekends
            continue
            
        day_bars = pd.date_range(
            start=date.replace(hour=9, minute=30),
            end=date.replace(hour=15, minute=55),
            freq='5min'
        )
        trading_bars.extend(day_bars)
    
    n_bars = len(trading_bars)
    print(f"📊 Generated {n_bars} 5-minute bars")
    
    # Create base price movement
    np.random.seed(42)
    base_price = 22000.0
    prices = []
    
    for i in range(n_bars):
        # Normal price movement
        change = np.random.normal(0.0001, 0.002)
        
        # Add explicit gaps every ~100 bars to create FVGs
        if i > 10 and i % 100 == 0:
            if np.random.random() > 0.5:
                # Create bullish gap (price jumps up)
                change = np.random.uniform(0.005, 0.015)  # 0.5% - 1.5% gap up
                print(f"Creating bullish gap at bar {i}: {change*100:.2f}%")
            else:
                # Create bearish gap (price jumps down)
                change = np.random.uniform(-0.015, -0.005)  # -0.5% to -1.5% gap down
                print(f"Creating bearish gap at bar {i}: {change*100:.2f}%")
        
        if i == 0:
            current_price = base_price
        else:
            current_price = prices[-1] * (1 + change)
        
        prices.append(current_price)
    
    prices = np.array(prices)
    
    # Create OHLC data with proper gaps
    data = pd.DataFrame(index=trading_bars)
    data['close'] = prices
    
    # Generate open, high, low
    data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
    
    # For bars with gaps, ensure the gap is visible in OHLC
    for i in range(1, len(data)):
        if data['open'].iloc[i] > data['close'].iloc[i-1] * 1.005:  # Bullish gap
            # Set high/low to maintain the gap
            data.loc[data.index[i], 'high'] = data['open'].iloc[i] * 1.002
            data.loc[data.index[i], 'low'] = max(data['close'].iloc[i-1] * 0.998, data['close'].iloc[i] * 0.998)
        elif data['open'].iloc[i] < data['close'].iloc[i-1] * 0.995:  # Bearish gap
            # Set high/low to maintain the gap
            data.loc[data.index[i], 'high'] = min(data['close'].iloc[i-1] * 1.002, data['open'].iloc[i] * 1.002)
            data.loc[data.index[i], 'low'] = data['open'].iloc[i] * 0.998
        else:
            # Normal bar
            volatility = np.random.uniform(0.001, 0.003)
            data.loc[data.index[i], 'high'] = max(data['open'].iloc[i], data['close'].iloc[i]) * (1 + volatility)
            data.loc[data.index[i], 'low'] = min(data['open'].iloc[i], data['close'].iloc[i]) * (1 - volatility)
    
    # Volume
    data['volume'] = np.random.poisson(500, len(data))
    
    print(f"✅ Created data: {len(data)} bars from {data.index[0]} to {data.index[-1]}")
    print(f"   Price range: ${data['low'].min():.2f} - ${data['high'].max():.2f}")
    
    return data

def detect_fvgs_simple(data):
    """Simple FVG detection based on 3-candle patterns"""
    print("\n=== Detecting FVGs ===")
    
    fvgs = []
    
    for i in range(2, len(data)):
        # Get last 3 candles
        candle1 = data.iloc[i-2]  # First candle
        candle2 = data.iloc[i-1]  # Middle candle  
        candle3 = data.iloc[i]    # Third candle
        
        # Bullish FVG: candle2.low > candle1.high
        if candle2.low > candle1.high:
            fvg_top = candle2.low
            fvg_bottom = candle1.high
            fvg_size = fvg_top - fvg_bottom
            
            if fvg_size > 0:  # Valid FVG
                fvgs.append({
                    'type': 'bullish',
                    'start_time': data.index[i-1],
                    'top': fvg_top,
                    'bottom': fvg_bottom,
                    'size': fvg_size,
                    'strength': fvg_size / candle1.close  # Relative strength
                })
                print(f"Found bullish FVG at {data.index[i-1]}: size={fvg_size:.2f} ({fvg_size/candle1.close*100:.3f}%)")
        
        # Bearish FVG: candle2.high < candle1.low
        elif candle2.high < candle1.low:
            fvg_top = candle1.low
            fvg_bottom = candle2.high
            fvg_size = fvg_top - fvg_bottom
            
            if fvg_size > 0:  # Valid FVG
                fvgs.append({
                    'type': 'bearish',
                    'start_time': data.index[i-1],
                    'top': fvg_top,
                    'bottom': fvg_bottom,
                    'size': fvg_size,
                    'strength': fvg_size / candle1.close  # Relative strength
                })
                print(f"Found bearish FVG at {data.index[i-1]}: size={fvg_size:.2f} ({fvg_size/candle1.close*100:.3f}%)")
    
    print(f"🔍 Detected {len(fvgs)} FVGs")
    
    # Filter by strength (keep only significant FVGs)
    fvgs = [fvg for fvg in fvgs if fvg['strength'] > 0.0001]  # 0.01% minimum
    print(f"📊 Filtered to {len(fvgs)} significant FVGs")
    
    return fvgs

def analyze_hold_times(data, fvgs):
    """Analyze how long FVGs take to fill"""
    print(f"\n=== Analyzing Hold Times for {len(fvgs)} FVGs ===")
    
    hold_times = []
    fill_results = []
    
    for i, fvg in enumerate(fvgs):
        # Find FVG start index
        start_idx = data.index.get_loc(fvg['start_time'])
        
        # Look ahead for fill (up to 5 trading days)
        max_bars = 5 * 24 * 12  # 5 days of 5-minute bars
        end_idx = min(start_idx + max_bars, len(data) - 1)
        
        filled = False
        fill_bar = None
        
        # Check each future bar for fill
        for j in range(start_idx + 1, end_idx + 1):
            current_bar = data.iloc[j]
            
            # Check if FVG is filled
            if fvg['type'] == 'bullish':
                if current_bar.low <= fvg['bottom']:
                    filled = True
                    fill_bar = j
                    break
            else:  # bearish
                if current_bar.high >= fvg['top']:
                    filled = True
                    fill_bar = j
                    break
        
        # Calculate hold time
        if filled and fill_bar:
            hold_bars = fill_bar - start_idx
            hold_minutes = hold_bars * 5  # 5-minute bars
            hold_hours = hold_minutes / 60
            hold_times.append(hold_hours)
            fill_results.append('filled')
        else:
            hold_times.append(40)  # Max 40 hours (5 days)
            fill_results.append('not_filled')
        
        # Progress update
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(fvgs)} FVGs...")
    
    # Calculate statistics
    hold_times = np.array(hold_times)
    
    print(f"\n📊 Hold Time Analysis Results:")
    print(f"  Total FVGs: {len(fvgs)}")
    print(f"  Filled: {sum(1 for r in fill_results if r == 'filled')} ({sum(1 for r in fill_results if r == 'filled')/len(fill_results)*100:.1f}%)")
    print(f"  Not filled: {sum(1 for r in fill_results if r == 'not_filled')} ({sum(1 for r in fill_results if r == 'not_filled')/len(fill_results)*100:.1f}%)")
    
    if len(hold_times) > 0:
        print(f"\n⏱️  Hold Time Statistics:")
        print(f"  Average: {np.mean(hold_times):.2f} hours")
        print(f"  Median: {np.median(hold_times):.2f} hours")
        print(f"  Min: {np.min(hold_times):.2f} hours")
        print(f"  Max: {np.max(hold_times):.2f} hours")
        print(f"  Std Dev: {np.std(hold_times):.2f} hours")
        
        # Distribution analysis
        under_30m = np.sum(hold_times < 0.5)
        under_1h = np.sum(hold_times < 1)
        under_2h = np.sum(hold_times < 2)
        under_4h = np.sum(hold_times < 4)
        under_8h = np.sum(hold_times < 8)
        under_24h = np.sum(hold_times < 24)
        
        print(f"\n📈 Hold Time Distribution:")
        print(f"  < 30 min: {under_30m} ({under_30m/len(hold_times)*100:.1f}%)")
        print(f"  < 1 hour: {under_1h} ({under_1h/len(hold_times)*100:.1f}%)")
        print(f"  < 2 hours: {under_2h} ({under_2h/len(hold_times)*100:.1f}%)")
        print(f"  < 4 hours: {under_4h} ({under_4h/len(hold_times)*100:.1f}%)")
        print(f"  < 8 hours: {under_8h} ({under_8h/len(hold_times)*100:.1f}%)")
        print(f"  < 24 hours: {under_24h} ({under_24h/len(hold_times)*100:.1f}%)")
    
    return {
        'total_fvgs': len(fvgs),
        'fill_rate': sum(1 for r in fill_results if r == 'filled') / len(fill_results) if fill_results else 0,
        'avg_hold_time': np.mean(hold_times) if len(hold_times) > 0 else 0,
        'median_hold_time': np.median(hold_times) if len(hold_times) > 0 else 0,
        'hold_times': hold_times.tolist() if len(hold_times) > 0 else []
    }

def main():
    """Main function"""
    print("FVG Hold Time Analysis - Fixed Version")
    print("=" * 50)
    
    try:
        # Create data with explicit FVGs
        data = create_data_with_fvgs()
        
        # Detect FVGs
        fvgs = detect_fvgs_simple(data)
        
        if not fvgs:
            print("❌ No FVGs detected")
            return False
        
        # Analyze hold times
        results = analyze_hold_times(data, fvgs)
        
        # Provide recommendations
        print(f"\n🎯 Key Findings:")
        print(f"  • Average FVG hold time: {results['avg_hold_time']:.2f} hours")
        print(f"  • Median hold time: {results['median_hold_time']:.2f} hours")
        print(f"  • Fill rate: {results['fill_rate']*100:.1f}%")
        
        # Trading recommendations
        avg_hold = results['avg_hold_time']
        fill_rate = results['fill_rate']
        
        print(f"\n💡 Trading Recommendations:")
        
        if avg_hold < 1:
            print(f"  • Use very short hold times (30-60 minutes)")
            print(f"  • Focus on quick scalping strategies")
        elif avg_hold < 4:
            print(f"  • Use short to medium hold times (1-4 hours)")
            print(f"  • Intraday trading works well")
        elif avg_hold < 12:
            print(f"  • Use medium hold times (4-12 hours)")
            print(f"  • Consider holding into next session")
        else:
            print(f"  • Use longer hold times (12+ hours)")
            print(f"  • Swing trading approach")
        
        if fill_rate > 0.7:
            print(f"  • High fill rate ({fill_rate*100:.1f}%) - FVGs are reliable")
        elif fill_rate > 0.5:
            print(f"  • Moderate fill rate ({fill_rate*100:.1f}%) - Be selective")
        else:
            print(f"  • Low fill rate ({fill_rate*100:.1f}%) - Requires confirmation")
        
        print(f"\n✅ Hold time analysis completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)