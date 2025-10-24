# QuantConnect Algorithm - Minimal Test

class SimpleTestAlgorithm(QCAlgorithm):
    """Minimal test algorithm for deployment verification."""
    
    def Initialize(self):
        """Initialize algorithm and set required data."""
        self.SetStartDate(2024, 1, 1)   # Set Start Date
        self.SetEndDate(2024, 1, 31)     # Set End Date (short period for testing)
        self.SetCash(100000)             # Set Strategy Cash
        
        # Add SPY as benchmark
        self.AddEquity("SPY", Resolution.Daily)
        
        self.Debug("Algorithm initialized successfully")
    
    def OnData(self, data):
        """OnData event is the primary entry point for your algorithm."""
        if self.IsWarmingUp:
            return
            
        # Simple buy and hold strategy
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1.0)
            self.Debug("Purchased SPY")