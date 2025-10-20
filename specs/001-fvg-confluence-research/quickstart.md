# Quick Start Guide: FVG Confluence Trading Strategy

**Date**: 2025-10-20  
**Feature**: FVG Confluence Trading Strategy Research

## Prerequisites

### QuantConnect Setup
1. Create QuantConnect account at [quantconnect.com](https://www.quantconnect.com)
2. Subscribe to MNQ futures data (CME exchange)
3. Set up paper trading account for testing

### Development Environment
- Python 3.11+
- QuantConnect LEAN framework (cloud-based)
- Basic understanding of futures trading concepts

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd FractalFVG
git checkout 001-fvg-confluence-research
```

### 2. Review Project Structure
```
src/
├── indicators/           # FVG detection indicators
├── strategy/            # Main trading algorithm
├── data/               # Data processing utilities
├── analysis/           # Performance analysis tools
└── utils/              # Configuration and helpers
```

### 3. Configure Strategy Parameters
Edit `src/utils/config.py`:
```python
STRATEGY_CONFIG = {
    "symbol": "MNQ",
    "timeframes": list(range(1, 61)),  # 1-60 minutes
    "volume_threshold": 2.0,
    "min_confluence_score": 70,
    "max_daily_trades": 20,
    "risk_per_trade": 0.02,  # 2% risk
    "ml_models": {
        "stop_loss": True,
        "take_profit": True,
        "timeframe_weighting": True
    }
}
```

## Quick Start Steps

### Step 1: Basic FVG Detection
```python
from src.indicators.fvg_indicator import FairValueGapIndicator

# Create FVG indicator for 15-minute timeframe
fvg_indicator = FairValueGapIndicator("FVG_15min")

# Process price bars
for bar in price_data:
    if fvg_indicator.update(bar):
        fvgs = fvg_indicator.get_current_fvgs()
        print(f"Detected {len(fvgs)} FVGs")
```

### Step 2: Multi-Timeframe Analysis
```python
from src.data.timeframe_manager import TimeframeManager

# Initialize multi-timeframe manager (1-60 minutes)
tf_manager = TimeframeManager("MNQ", list(range(1, 61)))

# Process tick data
for tick in tick_data:
    tf_manager.process_tick(tick)
    
# Get confluence areas
confluence_areas = tf_manager.get_confluence_scores()
```

### Step 3: Volume Confirmation
```python
from src.indicators.volume_fvg_indicator import VolumeWeightedFVGIndicator

# Create volume-enhanced FVG indicator
volume_fvg = VolumeWeightedFVGIndicator("VolumeFVG", min_volume=1000)

# Process bars with volume analysis
for bar in price_data:
    if volume_fvg.update(bar):
        if volume_fvg.value > 0.5:  # Strong signal
            print(f"High-confidence FVG detected")
```

### Step 4: Complete Strategy Setup with ML
```python
from src.strategy.fvg_confluence_algorithm import FVGConfluenceAlgorithm

# Initialize the main algorithm with ML models
algorithm = FVGConfluenceAlgorithm()
algorithm.enable_ml_features(
    dynamic_stop_loss=True,
    dynamic_take_profit=True,
    timeframe_weighting=True
)
algorithm.initialize()

# Run backtest
backtest_results = algorithm.run_backtest(
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_capital=100000
)

# Analyze results
print(f"Sharpe Ratio: {backtest_results.sharpe_ratio:.2f}")
print(f"Max Drawdown: {backtest_results.max_drawdown:.2%}")
print(f"Win Rate: {backtest_results.win_rate:.2%}")
print(f"ML Stop Loss Accuracy: {backtest_results.ml_stop_accuracy:.2%}")
print(f"ML Target Accuracy: {backtest_results.ml_target_accuracy:.2%}")
```

## Core Components Usage

### FVG Detection
```python
# Basic FVG detection
fvg_indicator = FairValueGapIndicator("FVG")
fvg_indicator.update(price_bar)

# Get detected gaps
current_fvgs = fvg_indicator.get_current_fvgs()
for fvg in current_fvgs:
    print(f"FVG: {fvg.type} at {fvg.price_level}, size: {fvg.gap_size}")
```

### Confluence Scoring
```python
from src.indicators.confluence_scorer import ConfluenceScorer

scorer = ConfluenceScorer()
confluence_score = scorer.calculate_confluence(fvgs, volume_data)

if confluence_score.weighted_score > 70:
    print(f"Strong confluence: {confluence_score.weighted_score}")
```

### ML-Enhanced Risk Management
```python
from src.strategy.ml_risk_manager import MLRiskManager

risk_manager = MLRiskManager(account_balance=100000)
ml_setup = risk_manager.calculate_ml_setup(
    confluence_score=85,
    volume_profile_data=volume_data,
    market_structure=structure_data,
    risk_percent=0.02
)

print(f"Entry: {ml_setup.entry_price}")
print(f"ML Stop Loss: {ml_setup.dynamic_stop_loss}")
print(f"ML Target: {ml_setup.dynamic_target}")
print(f"Position Size: {ml_setup.position_size} contracts")
print(f"ML Confidence: {ml_setup.ml_confidence:.2%}")
```

### Trade Filtering
```python
from src.strategy.trade_filter import TradeFilter

filter = TradeFilter(max_daily_trades=20, min_confidence=0.7)
filtered_setups = filter.filter_trades(all_setups)

print(f"Filtered to {len(filtered_setups)} high-quality setups")
```

## Running Your First Backtest

### 1. Prepare Data
```python
# Ensure MNQ data is available in QuantConnect
algorithm = FVGConfluenceAlgorithm()
algorithm.set_start_date(2024, 1, 1)
algorithm.set_end_date(2024, 3, 31)
algorithm.set_cash(100000)
```

### 2. Execute Backtest
```python
# Run the backtest
results = algorithm.run_backtest()

# Key metrics
print(f"Total Return: {results.total_return:.2%}")
print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
print(f"Max Drawdown: {results.max_drawdown:.2%}")
print(f"Win Rate: {results.win_rate:.2%}")
print(f"Profit Factor: {results.profit_factor:.2f}")
```

### 3. Analyze Trade Details
```python
# Export trade details
trades = results.get_trade_details()
for trade in trades[:10]:  # First 10 trades
    print(f"{trade.direction} {trade.entry_price} -> {trade.exit_price}")
    print(f"P&L: ${trade.pnl:.2f}, Duration: {trade.duration}")
```

## Paper Trading Setup

### 1. Configure Paper Trading
```python
# Enable paper trading mode
algorithm.set_paper_trading(True)
algorithm.set_brokerage_model(BrokerageName.InteractiveBrokers)

# Set realistic parameters
algorithm.set_security_initializer(lambda security: {
    'slippage': ConstantSlippageModel(0.02),
    'fee': ConstantFeeModel(0.25),
    'fill_model': ImmediateFillModel()
})
```

### 2. Monitor Performance
```python
# Real-time monitoring
def on_end_of_day():
    daily_metrics = algorithm.get_daily_performance()
    print(f"Daily P&L: ${daily_metrics.pnl:.2f}")
    print(f"Trades Today: {daily_metrics.trade_count}")

algorithm.schedule.on(
    algorithm.date_rules.every_day(),
    algorithm.time_rules.market_close(),
    on_end_of_day
)
```

## Common Use Cases

### 1. Research Mode
```python
# Analyze FVG patterns without trading
research_mode = True
algorithm.set_research_mode(research_mode)

# Export FVG data for analysis
fvg_data = algorithm.export_fvg_data()
fvg_data.to_csv("fvg_analysis.csv")
```

### 2. Strategy Optimization
```python
# Test different parameters
parameters = {
    "volume_threshold": [1.5, 2.0, 2.5],
    "min_confluence_score": [60, 70, 80],
    "timeframes": [[1,5,15], [5,15,30], [15,30,60]]
}

optimization_results = algorithm.optimize_parameters(parameters)
best_params = optimization_results.get_best_parameters()
```

### 3. Performance Monitoring
```python
# Set up alerts
algorithm.set_performance_alerts({
    "max_drawdown": 0.15,
    "min_sharpe": 1.0,
    "min_win_rate": 0.45
})

# Daily reports
algorithm.generate_daily_report()
```

## Troubleshooting

### Common Issues

1. **No FVGs Detected**
   - Check volume threshold settings
   - Verify timeframe configuration
   - Ensure sufficient historical data

2. **High Drawdown**
   - Reduce position sizing
   - Tighten stop losses
   - Increase minimum confluence score

3. **Low Trade Frequency**
   - Lower confluence requirements
   - Expand timeframe analysis
   - Reduce volume confirmation threshold

### Debug Mode
```python
# Enable detailed logging
algorithm.set_debug_mode(True)
algorithm.set_log_level("DEBUG")

# Export intermediate results
algorithm.export_debug_data("debug_output.csv")
```

## Next Steps

1. **Run Initial Backtest**: Test with default parameters on 6 months of data
2. **Parameter Optimization**: Fine-tune settings for your risk tolerance
3. **Paper Trading**: Validate strategy with real-time data
4. **Performance Monitoring**: Track metrics and adjust as needed
5. **Live Trading**: Gradually scale up after successful paper trading

## Support Resources

- **Documentation**: See `docs/` directory for detailed API documentation
- **Examples**: Check `examples/` directory for sample implementations
- **Tests**: Review `tests/` directory for usage patterns
- **QuantConnect Docs**: [docs.quantconnect.com](https://docs.quantconnect.com)

## Performance Benchmarks

Based on research findings, expect:
- **FVG Detection**: 50+ setups per month
- **Win Rate**: 45-55% with volume confirmation
- **Sharpe Ratio**: 1.0-1.5 (target >1.5)
- **Max Drawdown**: <15% (target <12%)
- **Trade Frequency**: 5-20 trades per day

Adjust expectations based on market conditions and your specific parameter settings.