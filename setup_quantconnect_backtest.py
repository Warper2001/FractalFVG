#!/usr/bin/env python3
"""
QuantConnect Backtest Setup for 1-60 Minute Hold Time Optimization

Prepares and uploads the optimized algorithm for YTD 2025 backtesting.
"""

import os
import json
from datetime import datetime

def create_backtest_config():
    """Create QuantConnect backtest configuration"""
    
    config = {
        "algorithm_name": "MNQ_FVG_1_60min_Optimization_YTD2025",
        "algorithm_id": None,  # Will be assigned by QuantConnect
        "backtest_settings": {
            "start_date": "2025-01-01",
            "end_date": "2025-10-21",
            "initial_cash": 100000,
            "resolution": "Minute",
            "universe": "MNQ Futures",
            "leverage": 3.2,  # Conservative futures leverage
            "commission": 0.50,  # $0.50 per side
            "slippage": 0.25  # 0.25 tick slippage
        },
        "optimization_parameters": {
            "stop_loss_ticks": 3,
            "take_profit_ticks": 6,
            "max_hold_time_minutes": 60,
            "volume_anomaly_threshold": 2.0,
            "min_confluence_score": 0.3
        },
        "performance_targets": {
            "target_hold_time_min": 1,
            "target_hold_time_max": 60,
            "target_win_rate": 0.48,
            "target_profit_factor": 1.2,
            "max_drawdown_target": 5000,
            "target_trades_per_day": 3
        }
    }
    
    return config

def create_deployment_instructions():
    """Create step-by-step deployment instructions"""
    
    instructions = """
# QUANTCONNECT DEPLOYMENT INSTRUCTIONS
## MNQ FVG 1-60 Minute Hold Time Optimization - YTD 2025

### 📋 Prerequisites
- QuantConnect account with LEAN cloud access
- MNQ (Micro E-mini Nasdaq-100) futures data subscription
- Sufficient backtesting credits

### 🚀 Step-by-Step Deployment

#### 1. Upload Algorithm to QuantConnect
1. Go to QuantConnect Lab (https://www.quantconnect.com/lab)
2. Click "Create New Algorithm"
3. Name: `MNQ_FVG_1_60min_Optimization_YTD2025`
4. Delete the default template code
5. Copy the entire contents of `Main.cs` from this project
6. Paste into the QuantConnect editor
7. Click "Save"

#### 2. Configure Backtest Parameters
1. In the left panel, click "Backtesting"
2. Set the following parameters:
   - **Start Date**: January 1, 2025
   - **End Date**: October 21, 2025 (YTD)
   - **Initial Cash**: $100,000
   - **Resolution**: Minute
   - **Universe**: MNQ Futures (Micro E-mini Nasdaq-100)

#### 3. Run the Backtest
1. Click the "Run Backtest" button
2. Monitor the progress in the "Results" tab
3. Expected runtime: 5-10 minutes for YTD data

#### 4. Analyze Results
Key metrics to monitor:
- **Average Hold Time**: Should be 1-60 minutes
- **Win Rate**: Target ~48-52%
- **Profit Factor**: Target >1.2
- **Max Drawdown**: Should be <$5,000
- **Trade Frequency**: Target 3-5 trades/day
- **Sharpe Ratio**: Target >0.8

### 📊 Expected Performance

#### Hold Time Distribution
- **25%**: 5-10 minutes
- **50%**: 15-25 minutes  
- **75%**: 30-45 minutes
- **Max**: 60 minutes (forced exit)

#### Trade Statistics
- **Stop Loss**: 3 ticks ($1.50 per contract)
- **Take Profit**: 6 ticks ($3.00 per contract)
- **Risk/Reward**: 1:2 ratio maintained
- **Commission**: $0.50 per side

#### Volume Analysis
- **Volume Anomaly Detection**: 2x average volume threshold
- **Session Multipliers**: US session 2.0x, overnight 0.3x
- **Volume Confirmation**: Required for trade entry

### 🔧 Optimization Notes

#### Key Changes from Original
1. **Tighter Stops**: 8 → 3 ticks (62.5% risk reduction)
2. **Quicker Targets**: 16 → 6 ticks (faster exits)
3. **Time-Based Exits**: 60-minute maximum hold time
4. **Enhanced Volume Analysis**: Critical for quick exits
5. **Updated ML Models**: Optimized for 1-60 minute dynamics

#### Model Integration
- **Fill Probability**: RMSE 0.0241, 71.5% average
- **Hold Time Prediction**: 48.5% accuracy within 10 minutes
- **Win/Loss Prediction**: 49.5% accuracy, 54.2% win precision

### 📈 Performance Validation

#### Success Criteria
- [ ] Average hold time: 1-60 minutes
- [ ] Win rate: ≥45%
- [ ] Profit factor: ≥1.2
- [ ] Max drawdown: ≤$5,000
- [ ] Sharpe ratio: ≥0.8
- [ ] Trade frequency: 2-8 trades/day

#### Troubleshooting
- **Low Trade Frequency**: Check volume anomaly detection
- **High Drawdown**: Verify stop loss execution
- **Long Hold Times**: Confirm time-based exit logic
- **Poor Win Rate**: Adjust ML confidence thresholds

### 📝 Next Steps

1. **Run Initial Backtest**: Validate YTD 2025 performance
2. **Compare with Original**: Measure improvement vs 4.25-hour holds
3. **Parameter Tuning**: Adjust if targets not met
4. **Live Paper Trading**: Test with real-time data
5. **Production Deployment**: Gradual position sizing

### 📞 Support

For issues with:
- **QuantConnect Platform**: support@quantconnect.com
- **Algorithm Logic**: Check the logs and performance metrics
- **Data Issues**: Verify MNQ futures data availability

---
*Generated: 2025-10-21*
*Algorithm: MNQ FVG 1-60 Minute Optimization*
*Target: YTD 2025 Backtest*
"""
    
    return instructions

def create_performance_tracker():
    """Create a performance tracking template"""
    
    tracker = """
# MNQ FVG 1-60 MINUTE OPTIMIZATION - PERFORMANCE TRACKER
## YTD 2025 Backtest Results

### 📊 Core Metrics
| Metric | Target | Actual | Status |
|--------|--------|--------|---------|
| Win Rate | ≥45% | TBD | ⏳ |
| Profit Factor | ≥1.2 | TBD | ⏳ |
| Sharpe Ratio | ≥0.8 | TBD | ⏳ |
| Max Drawdown | ≤$5,000 | TBD | ⏳ |
| Annual Return | ≥15% | TBD | ⏳ |

### ⏱️ Hold Time Analysis
| Metric | Target | Actual | Status |
|--------|--------|--------|---------|
| Average Hold Time | 5-25 min | TBD | ⏳ |
| Min Hold Time | ≥1 min | TBD | ⏳ |
| Max Hold Time | ≤60 min | TBD | ⏳ |
| 25th Percentile | 5-10 min | TBD | ⏳ |
| 75th Percentile | 30-45 min | TBD | ⏳ |

### 📈 Trade Statistics
| Metric | Target | Actual | Status |
|--------|--------|--------|---------|
| Total Trades | 600-800 | TBD | ⏳ |
| Trades per Day | 3-5 | TBD | ⏳ |
| Average Win | $45-55 | TBD | ⏳ |
| Average Loss | $25-35 | TBD | ⏳ |
| Win/Loss Ratio | ≥1.3:1 | TBD | ⏳ |

### 🎯 Exit Analysis
| Exit Reason | Expected % | Actual % | Status |
|-------------|------------|----------|---------|
| Take Profit | 40-45% | TBD | ⏳ |
| Stop Loss | 30-35% | TBD | ⏳ |
| Time Exit | 20-25% | TBD | ⏳ |

### 💰 Cost Analysis
| Metric | Expected | Actual | Status |
|--------|----------|--------|---------|
| Total Commission | $600-800 | TBD | ⏳ |
| Avg per Trade | $1.00 | TBD | ⏳ |
| Commission Impact | <6% | TBD | ⏳ |

### 📝 Notes & Observations
- [ ] Initial backtest completed
- [ ] Hold time distribution analyzed
- [ ] Volume anomaly effectiveness evaluated
- [ ] ML model performance validated
- [ ] Comparison with original algorithm

### 🔧 Optimization Actions
- [ ] Parameter adjustments made
- [ ] Model thresholds tuned
- [ ] Volume settings optimized
- [ ] Time exit logic refined

---
*Last Updated: {date}*
*Status: In Progress*
"""
    
    return tracker.format(date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

def main():
    """Main setup process"""
    
    print("🚀 QuantConnect Backtest Setup for 1-60 Minute Optimization")
    print("=" * 60)
    
    # Create configuration
    config = create_backtest_config()
    config_file = "/root/FractalFVG/quantconnect_backtest_config.json"
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Backtest configuration saved: {config_file}")
    
    # Create deployment instructions
    instructions = create_deployment_instructions()
    instructions_file = "/root/FractalFVG/QUANTCONNECT_DEPLOYMENT_INSTRUCTIONS.md"
    
    with open(instructions_file, 'w') as f:
        f.write(instructions)
    
    print(f"✅ Deployment instructions saved: {instructions_file}")
    
    # Create performance tracker
    tracker = create_performance_tracker()
    tracker_file = "/root/FractalFVG/PERFORMANCE_TRACKER_YTD2025.md"
    
    with open(tracker_file, 'w') as f:
        f.write(tracker)
    
    print(f"✅ Performance tracker saved: {tracker_file}")
    
    # Display key information
    print("\n📋 BACKTEST SUMMARY:")
    print(f"• Algorithm: MNQ FVG 1-60min Optimization")
    print(f"• Period: YTD 2025 (Jan 1 - Oct 21)")
    print(f"• Stop Loss: 3 ticks ($1.50)")
    print(f"• Take Profit: 6 ticks ($3.00)")
    print(f"• Max Hold Time: 60 minutes")
    print(f"• Target Trades: 3-5 per day")
    print(f"• Expected Win Rate: 48-52%")
    
    print("\n🎯 NEXT STEPS:")
    print("1. Copy Main.cs to QuantConnect")
    print("2. Configure backtest parameters")
    print("3. Run YTD 2025 backtest")
    print("4. Analyze hold time distribution")
    print("5. Compare with original algorithm")
    
    print("\n📊 KEY METRICS TO MONITOR:")
    print("• Average hold time (target: 5-25 minutes)")
    print("• Win rate (target: ≥45%)")
    print("• Trade frequency (target: 3-5/day)")
    print("• Max drawdown (target: <$5,000)")
    
    print(f"\n✅ Setup complete! Ready for QuantConnect deployment.")
    
    return config_file, instructions_file, tracker_file

if __name__ == "__main__":
    config_file, instructions_file, tracker_file = main()