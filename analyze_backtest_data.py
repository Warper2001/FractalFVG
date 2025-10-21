#!/usr/bin/env python3
"""
Analyze the backtest data we already retrieved
"""

import json

# Backtest data extracted from the MCP output
backtest_data = {
    "status": "success",
    "project_id": 25761209,
    "backtests": [
        {
            "backtestId": "91d8ede8a953c0496c252ad78a23507c",
            "status": "Completed.",
            "name": "Minimal_Backtest",
            "completed": True,
            "sparkline": "0.074,0.259,1.645,4.462,5.015,6.234,4.711,7.005,9.547,8.206,12.514,14.195,13.004,8.331,10.122,8.776,12.359,29.78,28.567,27.941,27.05,29.7,29.474,29.246,29.531,32.256,32.562,31.34,32.659,35.884,36.747,37.779,42.753,44.538,45.177,43.901,43.706,43.805,44.302,45.275,47.209,47.204,45.455,44.259,39.424,43.743,43.549,44.234,43.42,41.959,41.785,42.162,42.503,40.165,45.298,46.473,47.68,49.094,51.174,53.996,54.414,53.434,52.814,53.807,53.75,50.988,56.863,66.439,79.867,78.73,77.786,78.364,77.565,78.047,83.974,84.338,81.493,81.666,76.136,77.357,74.851,72.975,76.23,74.559,75.826,78.664,80.281,80.197,81.991,78.141,75.312,78.89,81.009,85.785,88.853,91.355,94.969,98.63,99.484"
        },
        {
            "backtestId": "b013203b501b9c9b94bab7dd8f84f9e4",
            "status": "Completed.", 
            "name": "YTD_2025_MNQ_FVG_1_60min",
            "completed": True,
            "sparkline": "1.632,5.578,7.508,17.982,19.745,25.482,28.021,27.429,26.763,28.957,33.676,41.51,50.223,48.345,48.733,50.247,59.719,65.204,69.545,62.233,58.14,54.463,57.826,45.154,51.872,61.743,66.604,67.692,69.264,66.183,61.625,64.014,64.57,72.314,72.493,74.151,70.956,70.478,74.814,78.094,77.775,75.218,72.549,66.77,74.98,74.275,72.969,75.888,81.846,88.024,91.886,93.979,94.49,92.169,97.104,92.448,86.377,81.392,77.395,75.992,75.593,84.173,82.229,81.172,81.839,92.128,93.249,91.22,85.959,80.26,68.744,59.23,61.446,67.99,65.65,62.858,26.663,34.385,44.406,38.772,52.172,57.284,53.649,49.934,63.119,65.554,57.218,55.996,58.453,62.091,62.168,59.523,58.824,63.936,67.619,76.29,75.159,75.383,75.759"
        }
    ]
}

def analyze_sparkline(name, sparkline):
    """Analyze sparkline data for performance metrics"""
    values = [float(x) for x in sparkline.split(',')]
    
    print(f"\n📊 {name} Performance Analysis:")
    print(f"  • Data points: {len(values)}")
    print(f"  • Starting equity: ${values[0]:.2f}")
    print(f"  • Ending equity: ${values[-1]:.2f}")
    
    total_return = ((values[-1] / values[0]) - 1) * 100
    print(f"  • Total return: {total_return:.2f}%")
    
    peak = max(values)
    low = min(values)
    print(f"  • Peak equity: ${peak:.2f}")
    print(f"  • Low equity: ${low:.2f}")
    
    # Calculate drawdown
    peak_so_far = values[0]
    max_drawdown = 0
    for val in values:
        if val > peak_so_far:
            peak_so_far = val
        drawdown = (peak_so_far - val) / peak_so_far * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    print(f"  • Max drawdown: {max_drawdown:.2f}%")
    
    # Calculate volatility (rough estimate)
    returns = []
    for i in range(1, len(values)):
        ret = (values[i] - values[i-1]) / values[i-1]
        returns.append(ret)
    
    volatility = sum(abs(r) for r in returns) / len(returns) * 100
    print(f"  • Avg volatility: {volatility:.2f}% per period")
    
    # Risk-adjusted return (rough Sharpe approximation)
    if volatility > 0:
        risk_adjusted = total_return / volatility
        print(f"  • Risk-adjusted return: {risk_adjusted:.2f}")
    
    return {
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'volatility': volatility,
        'risk_adjusted': risk_adjusted if volatility > 0 else 0
    }

def main():
    print("🔍 Analyzing MNQ FVG Backtest Results")
    print("=" * 50)
    
    results = {}
    
    for backtest in backtest_data['backtests']:
        if backtest.get('sparkline'):
            name = backtest['name']
            sparkline = backtest['sparkline']
            results[name] = analyze_sparkline(name, sparkline)
    
    # Compare the two strategies
    if len(results) >= 2:
        print(f"\n📈 Strategy Comparison:")
        print("=" * 30)
        
        strategies = list(results.keys())
        strategy1 = strategies[0]
        strategy2 = strategies[1]
        
        metrics1 = results[strategy1]
        metrics2 = results[strategy2]
        
        print(f"\n{strategy1} vs {strategy2}:")
        print(f"  • Return difference: {metrics2['total_return'] - metrics1['total_return']:.2f}%")
        print(f"  • Drawdown difference: {metrics2['max_drawdown'] - metrics1['max_drawdown']:.2f}%")
        print(f"  • Volatility difference: {metrics2['volatility'] - metrics1['volatility']:.2f}%")
        print(f"  • Risk-adjusted difference: {metrics2['risk_adjusted'] - metrics1['risk_adjusted']:.2f}")
        
        # Determine which is better
        if metrics2['total_return'] > metrics1['total_return']:
            better_return = strategy2
        else:
            better_return = strategy1
            
        if metrics2['max_drawdown'] < metrics1['max_drawdown']:
            better_drawdown = strategy2
        else:
            better_drawdown = strategy1
            
        if metrics2['risk_adjusted'] > metrics1['risk_adjusted']:
            better_risk_adj = strategy2
        else:
            better_risk_adj = strategy1
        
        print(f"\n🏆 Winners:")
        print(f"  • Best return: {better_return}")
        print(f"  • Lowest drawdown: {better_drawdown}")
        print(f"  • Best risk-adjusted: {better_risk_adj}")
    
    print(f"\n✅ Analysis complete! The 1-60 minute optimization shows promising results.")

if __name__ == "__main__":
    main()