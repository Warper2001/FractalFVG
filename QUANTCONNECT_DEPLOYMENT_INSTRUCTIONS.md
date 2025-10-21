
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
