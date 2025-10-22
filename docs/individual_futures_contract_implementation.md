# Individual Futures Contract Trading Implementation

Based on QuantConnect documentation research, this guide demonstrates how to implement individual futures contract trading using the `AddFutureContract` method.

## Key Concepts

### 1. Individual Contract Subscription
Instead of subscribing to an entire futures chain, you can trade specific contracts:

```python
# Get the futures chain
chain = self.FutureChainProvider.GetFutureContractChain(future_symbol, self.Time)

# Select specific contract (e.g., front month)
front_month_contract = min(chain, key=lambda x: x.Expiry)

# Add individual contract
contract_symbol = self.AddFutureContract(front_month_contract).Symbol
```

### 2. Contract Selection Methods

**Front Month Selection:**
```python
front_month_contract = min(chain, key=lambda x: x.Expiry)
```

**Specific Expiry Selection:**
```python
target_expiry = datetime(2024, 3, 15)
specific_contract = next(x for x in chain if x.Expiry.date() == target_expiry.date())
```

**Volume-Based Selection:**
```python
highest_volume_contract = max(chain, key=lambda x: x.Volume)
```

### 3. Contract Rollover Logic

```python
def SelectFrontMonthContract(self):
    chain = self.FutureChainProvider.GetFutureContractChain(self.future_symbol, self.Time)
    
    if not chain:
        return
    
    front_month_contract = min(chain, key=lambda x: x.Expiry)
    
    # Liquidate and remove old contract if different
    if self.current_contract and self.current_contract != front_month_contract:
        self.Liquidate(self.current_contract)
        self.RemoveSecurity(self.current_contract)
    
    # Add new contract
    self.contract_symbol = self.AddFutureContract(front_month_contract).Symbol
    self.current_contract = front_month_contract
```

## Complete Algorithm Structure

### Core Components

1. **Initialization:**
   - Set start/end dates and cash
   - Add future symbol for chain access
   - Schedule contract selection

2. **Contract Management:**
   - Select specific contracts from chain
   - Handle rollovers automatically
   - Remove expired contracts

3. **Trading Logic:**
   - Apply indicators to individual contracts
   - Generate signals based on contract data
   - Manage positions per contract

### Example Implementation

```python
from QuantConnect import *
from QuantConnect.Algorithm import *
from QuantConnect.Securities.Futures import *

class IndividualFuturesContractAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2024, 1, 1)
        self.SetEndDate(2024, 6, 30)
        self.SetCash(100000)
        
        # Add future for chain access
        self.future_symbol = self.AddFuture(Futures.Indices.SP500).Symbol
        
        # Initialize variables
        self.contract_symbol = None
        self.current_contract = None
        self.ema_short = None
        self.ema_long = None
        
        # Schedule monthly contract selection
        self.Schedule.On(self.DateRules.MonthStart(self.future_symbol), 
                        self.TimeRules.AfterMarketOpen(self.future_symbol, 0),
                        self.SelectFrontMonthContract)
        
        # Initial selection
        self.SelectFrontMonthContract()
    
    def SelectFrontMonthContract(self):
        chain = self.FutureChainProvider.GetFutureContractChain(self.future_symbol, self.Time)
        
        if not chain:
            return
        
        front_month_contract = min(chain, key=lambda x: x.Expiry)
        
        # Handle contract rollover
        if self.current_contract and self.current_contract != front_month_contract:
            self.Liquidate(self.current_contract)
            self.RemoveSecurity(self.current_contract)
        
        # Add new contract
        self.contract_symbol = self.AddFutureContract(front_month_contract).Symbol
        self.current_contract = front_month_contract
        
        # Initialize indicators
        self.ema_short = self.EMA(self.contract_symbol, 10, Resolution.Hour)
        self.ema_long = self.EMA(self.contract_symbol, 30, Resolution.Hour)
    
    def OnData(self, data):
        if not self.contract_symbol or not data.ContainsKey(self.contract_symbol):
            return
        
        price = data[self.contract_symbol].Price
        if price <= 0:
            return
        
        if not self.ema_short.IsReady or not self.ema_long.IsReady:
            return
        
        holdings = self.Portfolio[self.contract_symbol].Quantity
        
        # EMA crossover strategy
        if self.ema_short.Current.Value > self.ema_long.Current.Value:
            if holdings <= 0:
                self.SetHoldings(self.contract_symbol, 0.5)
        else:
            if holdings >= 0:
                self.SetHoldings(self.contract_symbol, -0.5)
```

## Advantages of Individual Contract Trading

### 1. **Precise Control**
- Trade specific contract months
- Target specific expiration dates
- Avoid unwanted contract exposure

### 2. **Cost Efficiency**
- Only subscribe to needed contracts
- Reduce data subscription costs
- Optimize memory usage

### 3. **Strategy Flexibility**
- Implement calendar spread strategies
- Trade contract-specific patterns
- Handle roll strategies explicitly

### 4. **Risk Management**
- Control exposure per contract
- Manage contract-specific risks
- Implement precise hedging

## Common Use Cases

### 1. **Front Month Trading**
```python
# Always trade the most active contract
front_month = min(chain, key=lambda x: x.Expiry)
```

### 2. **Calendar Spreads**
```python
# Trade spread between two contracts
near_contract = min(chain, key=lambda x: x.Expiry)
far_contract = sorted(chain, key=lambda x: x.Expiry)[1]

near_symbol = self.AddFutureContract(near_contract).Symbol
far_symbol = self.AddFutureContract(far_contract).Symbol
```

### 3. **Seasonal Strategies**
```python
# Trade specific contract months
target_month = 12  # December contracts
december_contracts = [x for x in chain if x.Expiry.month == target_month]
```

## Best Practices

### 1. **Contract Rollover**
- Always liquidate before removing contracts
- Schedule rollovers in advance
- Monitor contract expiration dates

### 2. **Data Management**
- Check data availability before trading
- Handle contract data gaps
- Validate price data quality

### 3. **Error Handling**
- Verify chain availability
- Handle contract addition failures
- Monitor indicator readiness

### 4. **Performance Optimization**
- Remove unused contracts
- Cache contract symbols
- Optimize indicator calculations

## Integration with Existing FVG Strategy

The individual contract approach can enhance the existing FVG (Fair Value Gap) strategy by:

1. **Targeted Contract Selection**: Select contracts with highest FVG probability
2. **Precise Entry/Exit**: Trade specific contract months for optimal fills
3. **Spread Trading**: Implement FVG-based calendar spreads
4. **Risk Management**: Control exposure per contract month

## Next Steps

1. **Implement in QuantConnect**: Convert the concept to actual QuantConnect algorithm
2. **Backtest Individual Contracts**: Test performance vs continuous contracts
3. **Optimize Contract Selection**: Use ML models for contract selection
4. **Integrate with FVG Detection**: Combine with existing FVG research

This implementation provides a solid foundation for precise futures contract trading within the QuantConnect ecosystem.