# QuantConnect Algorithm - Simple Buy and Hold Strategy

class TestAlgorithm(QCAlgorithm):
    """Simple test algorithm for deployment verification."""
    
    def Initialize(self):
        """Initialize algorithm and set required data."""
        self.SetStartDate(2024, 1, 1)   # Set Start Date
        self.SetEndDate(2024, 12, 31)    # Set End Date
        self.SetCash(100000)             # Set Strategy Cash
        
        # Add SPY as benchmark
        self.AddEquity("SPY", Resolution.Daily)
        
        # Set warm-up period
        self.SetWarmUp(TimeSpan(30))
        
        self.Debug("Algorithm initialized successfully")
    
    def OnData(self, data):
        """OnData event is the primary entry point for your algorithm."""
        if self.IsWarmingUp:
            return
            
        # Simple buy and hold strategy
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1.0)
            self.Debug("Purchased SPY")
    
    def OnEndOfDay(self, symbol):
        """End of day event handler."""
        if symbol.Value == "SPY":
            self.Debug(f"SPY End of Day: {self.Portfolio[symbol.Value].TotalPortfolioValue}")