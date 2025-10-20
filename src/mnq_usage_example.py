"""
Example usage of MNQDataAccess module in QuantConnect

This file demonstrates how to use the MNQDataAccess class in your QuantConnect algorithms.
Copy the relevant code sections into your QuantConnect algorithm files.

Author: FractalFVG Project
Date: 2025-10-20
"""

# This is the complete algorithm code you can use directly in QuantConnect
QUANTCONNECT_ALGORITHM_EXAMPLE = '''
from AlgorithmImports import *
from mnq_data_access import MNQDataAccess

class MNQTradingAlgorithm(QCAlgorithm):
    """
    Example MNQ trading algorithm using the MNQDataAccess module.
    This demonstrates various ways to access and trade MNQ futures.
    """
    
    def Initialize(self):
        # Set algorithm parameters
        self.SetStartDate(2024, 1, 1)
        self.SetEndDate(2024, 6, 30)
        self.SetCash(100000)
        
        # Initialize MNQ data access
        self.mnq = MNQDataAccess(self)
        
        # Example 1: Add front-month MNQ universe
        self.future = self.mnq.add_front_month_mnq(
            resolution=Resolution.Minute,
            extended_market_hours=True
        )
        
        # Example 2: Add custom filtered MNQ universe
        # Uncomment to use instead of front-month
        # self.future = self.mnq.add_mnq_universe(
        #     resolution=Resolution.Minute,
        #     min_expiry_days=1,
        #     max_expiry_days=90
        # )
        
        # Set up indicators
        self.ema_short = self.EMA(self.future.Symbol, 10, Resolution.Hour)
        self.ema_long = self.EMA(self.future.Symbol, 50, Resolution.Hour)
        
        # Warm up indicators
        self.WarmUpIndicator(self.future.Symbol, self.ema_short)
        self.WarmUpIndicator(self.future.Symbol, self.ema_long)
        
        # Schedule daily tasks
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen(self.future.Symbol, 30),
            self.check_market_conditions
        )
        
        # Schedule contract rollover check
        self.Schedule.On(
            self.DateRules.Every(DayOfWeek.Monday),
            self.TimeRules.BeforeMarketClose(self.future.Symbol, 60),
            self.check_contract_rollover
        )
        
        self.Log("MNQ Trading Algorithm Initialized")
    
    def OnData(self, data):
        # Get current prices
        continuous_price = self.mnq.get_continuous_price()
        mapped_price = self.mnq.get_mapped_contract_price()
        
        if not continuous_price or not mapped_price:
            return
        
        # Check if indicators are ready
        if not self.ema_short.IsReady or not self.ema_long.IsReady:
            return
        
        # Simple EMA crossover strategy
        ema_short_val = self.ema_short.Current.Value
        ema_long_val = self.ema_long.Current.Value
        
        # Trading logic
        if ema_short_val > ema_long_val and not self.Portfolio[self.future.Symbol].Invested:
            # Buy signal
            self.MarketOrder(self.future.Symbol, 1)
            self.Log(f"BUY: Continuous={continuous_price}, Mapped={mapped_price}")
            
        elif ema_short_val < ema_long_val and self.Portfolio[self.future.Symbol].Invested:
            # Sell signal
            self.Liquidate(self.future.Symbol)
            self.Log(f"SELL: Continuous={continuous_price}, Mapped={mapped_price}")
    
    def check_market_conditions(self):
        """Check market conditions and log relevant information"""
        # Get market hours
        market_hours = self.mnq.get_market_hours()
        self.Log(f"Market Hours: {market_hours}")
        
        # Check if market is open
        is_open = self.mnq.is_market_open()
        self.Log(f"Market Open: {is_open}")
        
        # Get current contract info
        front_month = self.mnq.get_front_month_contract()
        if front_month:
            self.Log(f"Front Month Contract: {front_month}")
        
        # Get contract expiries
        expiries = self.mnq.get_contract_expiries(days_ahead=60)
        for symbol, expiry in expiries[:3]:  # Show next 3 expiries
            self.Log(f"Contract {symbol} expires: {expiry}")
    
    def check_contract_rollover(self):
        """Check and perform contract rollover if needed"""
        if self.mnq.roll_to_front_month():
            self.Log("Contract rollover completed")
            
            # Re-warm up indicators after rollover
            self.WarmUpIndicator(self.future.Symbol, self.ema_short)
            self.WarmUpIndicator(self.future.Symbol, self.ema_long)
    
    def OnEndOfDay(self):
        """End of day tasks"""
        # Log daily performance
        self.Log(f"End of Day - Portfolio Value: {self.Portfolio.TotalPortfolioValue}")
        
        # Get margin requirement if invested
        if self.Portfolio.Invested:
            margin = self.mnq.get_margin_requirement()
            if margin:
                self.Log(f"Current Margin Requirement: {margin}")
'''

# Additional usage examples
USAGE_EXAMPLES = """
# Example 1: Basic MNQ universe subscription
mnq = MNQDataAccess(self)
future = mnq.add_mnq_universe()

# Example 2: Front-month only
future = mnq.add_front_month_mnq(resolution=Resolution.Minute)

# Example 3: Custom expiry range
future = mnq.add_mnq_universe(
    min_expiry_days=5,
    max_expiry_days=120,
    resolution=Resolution.Hour
)

# Example 4: Individual contract subscription
contract_symbol = Symbol.Create("MNQ", Market.CME, datetime(2024, 3, 15))
future = mnq.add_individual_mnq_contract(contract_symbol)

# Example 5: Get historical data
history = mnq.get_historical_mnq_data(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31),
    resolution=Resolution.Hour
)

# Example 6: Get current prices
continuous_price = mnq.get_continuous_price()
mapped_price = mnq.get_mapped_contract_price()

# Example 7: Contract management
front_month = mnq.get_front_month_contract()
contracts_by_expiry = mnq.get_contracts_by_expiry_range(min_days=1, max_days=90)
upcoming_expiries = mnq.get_contract_expiries(days_ahead=180)

# Example 8: Market information
is_open = mnq.is_market_open()
market_hours = mnq.get_market_hours()

# Example 9: Position management
mnq.roll_to_front_month()
margin_req = mnq.get_margin_requirement(quantity=2)
contract_value = mnq.calculate_contract_value(price=15000.0)
"""


def get_algorithm_code():
    """Return the complete algorithm code for QuantConnect"""
    return QUANTCONNECT_ALGORITHM_EXAMPLE


def get_usage_examples():
    """Return usage examples"""
    return USAGE_EXAMPLES


if __name__ == "__main__":
    print("MNQ Data Access Usage Examples")
    print("=" * 50)
    print("\nThis file contains examples for using the MNQDataAccess module.")
    print("Copy the algorithm code into your QuantConnect project.")
    print("\nKey features demonstrated:")
    print("- Front-month MNQ subscription")
    print("- EMA crossover strategy")
    print("- Contract rollover management")
    print("- Market hours and conditions checking")
    print("- Historical data retrieval")
    print("- Margin and position management")
