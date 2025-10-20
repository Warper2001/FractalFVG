#!/usr/bin/env python3
"""
Final Hold Time Analysis for FVG Strategy
Directly creates FVG scenarios to test hold times
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def create_fvg_scenarios():
    """Create specific FVG scenarios with known hold times"""
    print("=== Creating FVG Scenarios ===")
    
    # Create 5 days of 5-minute data
    end_date = datetime(2024, 3, 15)
    start_date = end_date - timedelta(days=5)
    
    # Generate trading hours
    trading_bars = []
    for date in pd.date_range(start=start_date, end=end_date, freq='D'):
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
    
    # Start with base price
    base_price = 22000.0
    data = pd.DataFrame(index=trading_bars)
    
    # Initialize with normal price movement
    np.random.seed(42)
    returns = np.random.normal(0.0001, 0.001, n_bars)
    prices = [base_price]
    
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    
    prices = prices[1:]
    data['close'] = prices
    
    # Create basic OHLC
    data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
    data['high'] = np.maximum(data['open'], data['close']) * 1.001
    data['low'] = np.minimum(data['open'], data['close']) * 0.999
    data['volume'] = np.random.poisson(500, n_bars)
    
    # Now insert specific FVG scenarios
    scenarios = []
    
    # Scenario 1: Bullish FVG that fills quickly (30 minutes)
    fvg_start_1 = 100  # Bar index
    gap_size_1 = base_price * 0.008  # 0.8% gap
    
    # Create bullish gap: candle2.low > candle1.high
    data.loc[data.index[fvg_start_1], 'high'] = data['close'].iloc[fvg_start_1] * 1.002
    data.loc[data.index[fvg_start_1], 'low'] = data['close'].iloc[fvg_start_1] * 0.998
    
    data.loc[data.index[fvg_start_1 + 1], 'open'] = data['close'].iloc[fvg_start_1] * (1 + gap_size_1/base_price)
    data.loc[data.index[fvg_start_1 + 1], 'low'] = data['open'].iloc[fvg_start_1 + 1] * 0.999
    data.loc[data.index[fvg_start_1 + 1], 'high'] = data['open'].iloc[fvg_start_1 + 1] * 1.001
    data.loc[data.index[fvg_start_1 + 1], 'close'] = data['open'].iloc[fvg_start_1 + 1] * 1.0005
    
    # Fill the FVG after 6 bars (30 minutes)
    fill_bar_1 = fvg_start_1 + 6
    data.loc[data.index[fill_bar_1], 'low'] = data['close'].iloc[fvg_start_1] * 0.995  # Fill the gap
    
    scenarios.append({
        'type': 'bullish',
        'start_bar': fvg_start_1,
        'fill_bar': fill_bar_1,
        'expected_hold_hours': 0.5
    })
    
    # Scenario 2: Bearish FVG that fills slowly (4 hours)
    fvg_start_2 = 200
    gap_size_2 = base_price * 0.012  # 1.2% gap
    
    # Create bearish gap: candle2.high < candle1.low
    data.loc[data.index[fvg_start_2], 'high'] = data['close'].iloc[fvg_start_2] * 1.002
    data.loc[data.index[fvg_start_2], 'low'] = data['close'].iloc[fvg_start_2] * 0.998
    
    data.loc[data.index[fvg_start_2 + 1], 'open'] = data['close'].iloc[fvg_start_2] * (1 - gap_size_2/base_price)
    data.loc[data.index[fvg_start_2 + 1], 'high'] = data['open'].iloc[fvg_start_2 + 1] * 1.001
    data.loc[data.index[fvg_start_2 + 1], 'low'] = data['open'].iloc[fvg_start_2 + 1] * 0.999
    data.loc[data.index[fvg_start_2 + 1], 'close'] = data['open'].iloc[fvg_start_2 + 1] * 0.9995
    
    # Fill the FVG after 48 bars (4 hours)
    fill_bar_2 = fvg_start_2 + 48
    data.loc[data.index[fill_bar_2], 'high'] = data['close'].iloc[fvg_start_2] * 1.005  # Fill the gap
    
    scenarios.append({
        'type': 'bearish',
        'start_bar': fvg_start_2,
        'fill_bar': fill_bar_2,
        'expected_hold_hours': 4.0
    })
    
    # Scenario 3: Bullish FVG that doesn't fill (unfilled)
    fvg_start_3 = 350
    gap_size_3 = base_price * 0.006  # 0.6% gap
    
    # Create bullish gap
    data.loc[data.index[fvg_start_3], 'high'] = data['close'].iloc[fvg_start_3] * 1.002
    data.loc[data.index[fvg_start_3], 'low'] = data['close'].iloc[fvg_start_3] * 0.998
    
    data.loc[data.index[fvg_start_3 + 1], 'open'] = data['close'].iloc[fvg_start_3] * (1 + gap_size_3/base_price)
    data.loc[data.index[fvg_start_3 + 1], 'low'] = data['open'].iloc[fvg_start_3 + 1] * 0.999
    data.loc[data.index[fvg_start_3 + 1], 'high'] = data['open'].iloc[fvg_start_3 + 1] * 1.001
    data.loc[data.index[fvg_start_3 + 1], 'close'] = data['open'].iloc[fvg_start_3 + 1] * 1.0005
    
    # Don't fill this FVG (keep price above gap)
    for i in range(fvg_start_3 + 2, min(fvg_start_3 + 100, len(data))):
        data.loc[data.index[i], 'low'] = max(data['low'].iloc[i], data['close'].iloc[fvg_start_3] * 1.002)
    
    scenarios.append({
        'type': 'bullish',
        'start_bar': fvg_start_3,
        'fill_bar': None,
        'expected_hold_hours': 40.0  # Max time (unfilled)
    })
    
    # Scenario 4: Bearish FVG with medium fill time (2 hours)
    fvg_start_4 = min(450, n_bars - 50)  # Ensure within bounds
    gap_size_4 = base_price * 0.010  # 1.0% gap
    
    # Create bearish gap
    data.loc[data.index[fvg_start_4], 'high'] = data['close'].iloc[fvg_start_4] * 1.002
    data.loc[data.index[fvg_start_4], 'low'] = data['close'].iloc[fvg_start_4] * 0.998
    
    data.loc[data.index[fvg_start_4 + 1], 'open'] = data['close'].iloc[fvg_start_4] * (1 - gap_size_4/base_price)
    data.loc[data.index[fvg_start_4 + 1], 'high'] = data['open'].iloc[fvg_start_4 + 1] * 1.001
    data.loc[data.index[fvg_start_4 + 1], 'low'] = data['open'].iloc[fvg_start_4 + 1] * 0.999
    data.loc[data.index[fvg_start_4 + 1], 'close'] = data['open'].iloc[fvg_start_4 + 1] * 0.9995
    
    # Fill after 24 bars (2 hours)
    fill_bar_4 = fvg_start_4 + 24
    data.loc[data.index[fill_bar_4], 'high'] = data['close'].iloc[fvg_start_4] * 1.003
    
    scenarios.append({
        'type': 'bearish',
        'start_bar': fvg_start_4,
        'fill_bar': fill_bar_4,
        'expected_hold_hours': 2.0
    })
    
    print(f"✅ Created {len(scenarios)} FVG scenarios")
    for i, scenario in enumerate(scenarios, 1):
        status = f"fills after {scenario['expected_hold_hours']}h" if scenario['fill_bar'] else "unfilled"
        print(f"  Scenario {i}: {scenario['type']} FVG - {status}")
    
    return data, scenarios

def detect_fvgs_simple(data):
    """Detect FVGs in the data"""
    print("\n=== Detecting FVGs ===")
    
    fvgs = []
    
    for i in range(2, len(data)):
        candle1 = data.iloc[i-2]
        candle2 = data.iloc[i-1]
        
        # Bullish FVG: candle2.low > candle1.high
        if candle2.low > candle1.high:
            fvg_top = candle2.low
            fvg_bottom = candle1.high
            fvg_size = fvg_top - fvg_bottom
            
            if fvg_size > 0:
                fvgs.append({
                    'type': 'bullish',
                    'start_time': data.index[i-1],
                    'start_bar': i-1,
                    'top': fvg_top,
                    'bottom': fvg_bottom,
                    'size': fvg_size,
                    'strength': fvg_size / candle1.close
                })
                print(f"Found bullish FVG at bar {i-1}: size={fvg_size:.2f}")
        
        # Bearish FVG: candle2.high < candle1.low
        elif candle2.high < candle1.low:
            fvg_top = candle1.low
            fvg_bottom = candle2.high
            fvg_size = fvg_top - fvg_bottom
            
            if fvg_size > 0:
                fvgs.append({
                    'type': 'bearish',
                    'start_time': data.index[i-1],
                    'start_bar': i-1,
                    'top': fvg_top,
                    'bottom': fvg_bottom,
                    'size': fvg_size,
                    'strength': fvg_size / candle1.close
                })
                print(f"Found bearish FVG at bar {i-1}: size={fvg_size:.2f}")
    
    print(f"🔍 Detected {len(fvgs)} FVGs")
    return fvgs

def analyze_hold_times(data, fvgs, scenarios):
    """Analyze hold times for detected FVGs"""
    print(f"\n=== Analyzing Hold Times ===")
    
    hold_times = []
    fill_results = []
    
    for fvg in fvgs:
        start_idx = fvg['start_bar']
        
        # Look ahead for fill (up to 5 days)
        max_bars = 5 * 24 * 12
        end_idx = min(start_idx + max_bars, len(data) - 1)
        
        filled = False
        fill_bar = None
        
        for j in range(start_idx + 1, end_idx + 1):
            current_bar = data.iloc[j]
            
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
        
        if filled and fill_bar:
            hold_bars = fill_bar - start_idx
            hold_hours = hold_bars * 5 / 60  # Convert 5-min bars to hours
            hold_times.append(hold_hours)
            fill_results.append('filled')
            print(f"FVG at bar {start_idx}: Filled after {hold_hours:.2f} hours")
        else:
            hold_times.append(40)  # Max time
            fill_results.append('not_filled')
            print(f"FVG at bar {start_idx}: Not filled within 5 days")
    
    # Compare with expected scenarios
    print(f"\n📊 Scenario Analysis:")
    for scenario in scenarios:
        expected = scenario['expected_hold_hours']
        actual = None
        
        # Find corresponding FVG
        for fvg in fvgs:
            if abs(fvg['start_bar'] - scenario['start_bar']) <= 2:  # Allow small offset
                if fvg['type'] == scenario['type']:
                    idx = fvgs.index(fvg)
                    actual = hold_times[idx]
                    break
        
        if actual is not None:
            status = "✅" if abs(actual - expected) < 0.5 else "⚠️"
            print(f"  {status} {scenario['type']} FVG: Expected {expected}h, Actual {actual:.2f}h")
        else:
            print(f"  ❌ {scenario['type']} FVG: Not found in detection")
    
    # Calculate statistics
    hold_times = np.array(hold_times)
    
    print(f"\n📈 Hold Time Statistics:")
    print(f"  Total FVGs: {len(fvgs)}")
    print(f"  Filled: {sum(1 for r in fill_results if r == 'filled')}")
    print(f"  Not filled: {sum(1 for r in fill_results if r == 'not_filled')}")
    
    if len(hold_times) > 0:
        print(f"  Average hold time: {np.mean(hold_times):.2f} hours")
        print(f"  Median hold time: {np.median(hold_times):.2f} hours")
        print(f"  Min hold time: {np.min(hold_times):.2f} hours")
        print(f"  Max hold time: {np.min(hold_times[hold_times < 40]):.2f} hours (excluding unfilled)")
    
    return {
        'total_fvgs': len(fvgs),
        'avg_hold_time': np.mean(hold_times) if len(hold_times) > 0 else 0,
        'median_hold_time': np.median(hold_times) if len(hold_times) > 0 else 0,
        'hold_times': hold_times.tolist() if len(hold_times) > 0 else []
    }

def main():
    """Main function"""
    print("FVG Hold Time Analysis - Final Version")
    print("=" * 50)
    
    try:
        # Create FVG scenarios
        data, scenarios = create_fvg_scenarios()
        
        # Detect FVGs
        fvgs = detect_fvgs_simple(data)
        
        if not fvgs:
            print("❌ No FVGs detected")
            return False
        
        # Analyze hold times
        results = analyze_hold_times(data, fvgs, scenarios)
        
        # Provide recommendations
        print(f"\n🎯 Key Findings:")
        print(f"  • Average FVG hold time: {results['avg_hold_time']:.2f} hours")
        print(f"  • Median hold time: {results['median_hold_time']:.2f} hours")
        
        print(f"\n💡 Trading Recommendations:")
        avg_hold = results['avg_hold_time']
        
        if avg_hold < 2:
            print(f"  • Use short hold times (30 minutes - 2 hours)")
            print(f"  • Suitable for day trading and scalping")
        elif avg_hold < 8:
            print(f"  • Use medium hold times (2-8 hours)")
            print(f"  • Good for intraday swing trading")
        else:
            print(f"  • Use longer hold times (8+ hours)")
            print(f"  • Consider swing or position trading")
        
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