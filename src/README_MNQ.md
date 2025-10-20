# MNQ Data Access Module

## Overview

The MNQ Data Access Module provides comprehensive functionality for accessing and working with MNQ (Micro E-mini Nasdaq-100 Index Futures) data in QuantConnect LEAN algorithms.

## Files

- `mnq_data_access.py` - Main MNQ data access class
- `mnq_usage_example.py` - Complete algorithm examples and usage patterns
- `README_MNQ.md` - This documentation file

## Quick Start

### 1. Import Required Modules

In your QuantConnect algorithm, add these imports:

```python
from AlgorithmImports import *
from mnq_data_access import MNQDataAccess
```

### 2. Initialize MNQ Data Access

```python
def Initialize(self):
    # Set up your algorithm parameters
    self.SetStartDate(2024, 1, 1)
    self.SetEndDate(2024, 12, 31)
    self.SetCash(100000)
    
    # Initialize MNQ data access
    self.mnq = MNQDataAccess(self)
```

### 3. Add MNQ Data

#### Front-Month Contract (Most Common)
```python
future = self.mnq.add_front_month_mnq(
    resolution=Resolution.Minute,
    extended_market_hours=True
)
```

#### Custom Expiry Range
```python
future = self.mnq.add_mnq_universe(
    min_expiry_days=1,
    max_expiry_days=90,
    resolution=Resolution.Minute
)
```

#### Individual Contract
```python
contract_symbol = Symbol.Create("MNQ", Market.CME, datetime(2024, 3, 15))
future = self.mnq.add_individual_mnq_contract(contract_symbol)
```

## Key Features

### Data Access Methods

- **`add_mnq_universe()`** - Add MNQ futures universe with custom filtering
- **`add_front_month_mnq()`** - Add only the front-month contract
- **`add_individual_mnq_contract()`** - Add a specific contract by symbol
- **`get_historical_mnq_data()`** - Retrieve historical OHLCV data

### Price Information

- **`get_continuous_price()`** - Get continuous contract price
- **`get_mapped_contract_price()`** - Get raw price of current contract
- **`get_mnq_chain()`** - Get the complete futures chain

### Contract Management

- **`get_front_month_contract()`** - Get front-month contract symbol
- **`get_contracts_by_expiry_range()`** - Filter contracts by expiry
- **`get_contract_expiries()`** - Get upcoming contract expiries
- **`roll_to_front_month()`** - Automated contract rollover

### Market Information

- **`is_market_open()`** - Check if MNQ market is open
- **`get_market_hours()`** - Get today's market hours
- **`calculate_contract_value()`** - Calculate notional contract value
- **`get_margin_requirement()`** - Get margin requirements

## Complete Algorithm Example

See `mnq_usage_example.py` for a complete working algorithm that demonstrates:

- EMA crossover strategy
- Contract rollover management
- Market condition monitoring
- Historical data analysis

## MNQ Contract Specifications

- **Symbol**: MNQ (Micro E-mini Nasdaq-100)
- **Exchange**: CME (Chicago Mercantile Exchange)
- **Contract Size**: $2 per index point
- **Tick Size**: 0.25 index points
- **Trading Hours**: Sunday 18:00 - Friday 17:00 ET
- **Expiry**: Quarterly (March, June, September, December)

## Data Normalization

The module supports various data normalization modes:

- **BackwardsRatio** (default) - Adjusts for contract rolls using ratios
- **BackwardsPanamaCanal** - Uses Panama Canal method
- **Forward** - Forward adjustment
- **None** - Raw prices without adjustment

## Common Usage Patterns

### 1. Simple Trend Following

```python
def OnData(self, data):
    price = self.mnq.get_continuous_price()
    if price > self.sma.Current.Value and not self.Portfolio.Invested:
        self.MarketOrder(self.mnq._future_symbol, 1)
    elif price < self.sma.Current.Value and self.Portfolio.Invested:
        self.Liquidate()
```

### 2. Contract Rollover

```python
def check_rollover(self):
    if self.mnq.roll_to_front_month():
        self.Log("Rolled to new front-month contract")
        # Re-warm up indicators if needed
        self.WarmUpIndicator(self.mnq._future_symbol, self.sma)
```

### 3. Historical Analysis

```python
def analyze_historical_data(self):
    history = self.mnq.get_historical_mnq_data(
        start_date=self.Time - timedelta(days=30),
        end_date=self.Time,
        resolution=Resolution.Hour
    )
    
    if not history.empty:
        avg_volume = history['volume'].mean()
        price_range = history['high'].max() - history['low'].min()
        self.Log(f"Avg Volume: {avg_volume}, Price Range: {price_range}")
```

## Error Handling

The module includes built-in error handling:

- Validates symbol availability before operations
- Returns None for unavailable data
- Raises descriptive errors for invalid operations
- Logs important events and warnings

## Performance Considerations

- Use appropriate resolution for your strategy (Minute for intraday, Daily for swing)
- Warm up indicators before using them in trading logic
- Consider data normalization mode for backtesting accuracy
- Monitor margin requirements for position sizing

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `AlgorithmImports` is imported before `MNQDataAccess`
2. **No Data Available**: Check market hours and contract expiry dates
3. **Indicator Not Ready**: Use `WarmUpIndicator()` or check `IsReady` property
4. **Contract Rollover**: Schedule regular rollover checks

### Debug Tips

- Use `self.Log()` to track contract symbols and prices
- Monitor market hours with `get_market_hours()`
- Check futures chain with `get_mnq_chain()` for available contracts
- Verify margin requirements before placing orders

## Integration with FractalFVG

This module is part of the FractalFVG project's research into futures volume gaps (FVG) and market microstructure. It provides the foundational data access layer for:

- FVG detection algorithms
- Volume profile analysis
- Market microstructure research
- Automated trading strategies

## Support

For issues or questions related to this module:

1. Check the QuantConnect documentation for futures data
2. Review the example algorithms in `mnq_usage_example.py`
3. Ensure proper import structure in your algorithm
4. Verify market hours and contract availability

## Version History

- **v1.0** (2025-10-20) - Initial release with comprehensive MNQ data access functionality