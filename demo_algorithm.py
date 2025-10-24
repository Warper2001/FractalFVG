# Demo MNQ Trading Algorithm
# Simple moving average crossover strategy for demonstration

class MNQTradingAlgorithm:
    def __init__(self):
        self.fast_period = 10
        self.slow_period = 30
        self.symbol = "MNQ"
        
    def initialize(self):
        """Initialize the algorithm"""
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(100000)
        
        # Add the underlying asset
        self.add_equity(self.symbol, Resolution.MINUTE)
        
        # Create moving averages
        self.fast_ma = self.sma(self.symbol, self.fast_period, Resolution.MINUTE)
        self.slow_ma = self.sma(self.symbol, self.slow_period, Resolution.MINUTE)
        
    def on_data(self, data):
        """Handle data updates"""
        if not self.fast_ma.is_ready or not self.slow_ma.is_ready:
            return
            
        # Get current values
        fast_value = self.fast_ma.current.value
        slow_value = self.slow_ma.current.value
        current_price = data[self.symbol].close
        
        # Trading logic
        if fast_value > slow_value and not self.portfolio.invested:
            # Buy signal
            self.set_holdings(self.symbol, 1.0)
            self.debug(f"BUY {self.symbol} at {current_price}")
            
        elif fast_value < slow_value and self.portfolio.invested:
            # Sell signal
            self.liquidate(self.symbol)
            self.debug(f"SELL {self.symbol} at {current_price}")