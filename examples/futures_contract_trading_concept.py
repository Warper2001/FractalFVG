"""
Futures Contract Trading Concept
Educational example showing individual futures contract trading logic
This demonstrates the concepts from QuantConnect documentation
"""

class FuturesContractTradingConcept:
    """
    Conceptual implementation of individual futures contract trading
    Based on QuantConnect AddFutureContract method documentation
    """
    
    def __init__(self):
        self.future_symbol = "ES"  # S&P 500 E-mini
        self.current_contract = None
        self.contract_symbol = None
        self.ema_short = None
        self.ema_long = None
        self.portfolio_value = 100000
        self.holdings = 0
        
    def select_front_month_contract(self, futures_chain):
        """
        Select the front-month contract from futures chain
        Equivalent to: min(chain, key=lambda x: x.Expiry)
        """
        if not futures_chain:
            return None
            
        # Find contract with lowest expiry (front month)
        front_month = min(futures_chain, key=lambda contract: contract['expiry'])
        return front_month
    
    def add_individual_contract(self, contract):
        """
        Add individual futures contract
        Equivalent to: AddFutureContract(contract_symbol)
        """
        self.contract_symbol = f"{self.future_symbol}_{contract['expiry'].strftime('%Y%m')}"
        self.current_contract = contract
        print(f"Added contract: {self.contract_symbol}")
        return self.contract_symbol
    
    def initialize_indicators(self):
        """
        Initialize technical indicators for the contract
        """
        # In QuantConnect: self.ema_short = self.EMA(self.contract_symbol, 10, Resolution.Hour)
        # self.ema_long = self.EMA(self.contract_symbol, 30, Resolution.Hour)
        self.ema_short = {'period': 10, 'values': []}
        self.ema_long = {'period': 30, 'values': []}
        print("Initialized EMA indicators")
    
    def calculate_ema(self, current_price, indicator):
        """
        Calculate Exponential Moving Average
        Simplified version for demonstration
        """
        alpha = 2 / (indicator['period'] + 1)
        
        if not indicator['values']:
            indicator['values'].append(current_price)
        else:
            ema = alpha * current_price + (1 - alpha) * indicator['values'][-1]
            indicator['values'].append(ema)
        
        # Keep only recent values
        if len(indicator['values']) > indicator['period']:
            indicator['values'] = indicator['values'][-indicator['period']:]
        
        return indicator['values'][-1]
    
    def trading_logic(self, current_price):
        """
        Main trading logic based on EMA crossover
        """
        if not self.ema_short or not self.ema_long:
            return
        
        # Calculate current EMAs
        ema_short_current = self.calculate_ema(current_price, self.ema_short)
        ema_long_current = self.calculate_ema(current_price, self.ema_long)
        
        # Check if we have enough data
        if len(self.ema_short['values']) < self.ema_short['period']:
            print(f"Collecting data: {len(self.ema_short['values'])}/{self.ema_short['period']}")
            return
        
        # Trading signals
        if ema_short_current > ema_long_current:
            # Bullish signal
            if self.holdings <= 0:
                self.holdings = int(self.portfolio_value * 0.5 / current_price)
                print(f"LONG signal at {current_price:.2f}, Holdings: {self.holdings}")
        else:
            # Bearish signal
            if self.holdings >= 0:
                self.holdings = -int(self.portfolio_value * 0.5 / current_price)
                print(f"SHORT signal at {current_price:.2f}, Holdings: {self.holdings}")
    
    def handle_contract_rollover(self, new_futures_chain):
        """
        Handle contract rollover when current contract expires
        """
        new_contract = self.select_front_month_contract(new_futures_chain)
        
        if new_contract and new_contract != self.current_contract:
            print(f"Rolling over from {self.contract_symbol} to new contract")
            
            # Liquidate current position
            if self.holdings != 0:
                print(f"Liquidating {self.holdings} contracts")
                self.holdings = 0
            
            # Add new contract
            self.add_individual_contract(new_contract)
            self.initialize_indicators()
    
    def get_status(self):
        """
        Get current trading status
        """
        status = {
            'contract_symbol': self.contract_symbol,
            'holdings': self.holdings,
            'ema_short_current': self.ema_short['values'][-1] if self.ema_short and self.ema_short['values'] else None,
            'ema_long_current': self.ema_long['values'][-1] if self.ema_long and self.ema_long['values'] else None
        }
        return status


# Example usage
def demo_futures_trading():
    """
    Demonstrate the futures contract trading concept
    """
    trader = FuturesContractTradingConcept()
    
    # Simulate futures chain data
    futures_chain = [
        {'symbol': 'ES', 'expiry': pd.Timestamp('2024-03-15'), 'price': 4500},
        {'symbol': 'ES', 'expiry': pd.Timestamp('2024-06-15'), 'price': 4520},
        {'symbol': 'ES', 'expiry': pd.Timestamp('2024-09-15'), 'price': 4540},
    ]
    
    # Select and add front-month contract
    front_contract = trader.select_front_month_contract(futures_chain)
    trader.add_individual_contract(front_contract)
    trader.initialize_indicators()
    
    # Simulate price data and trading
    prices = [4500, 4510, 4520, 4515, 4530, 4540, 4535, 4525, 4510, 4505]
    
    print("=== Trading Simulation ===")
    for i, price in enumerate(prices):
        print(f"\nBar {i+1}: Price = {price}")
        trader.trading_logic(price)
    
    print(f"\nFinal Status: {trader.get_status()}")


if __name__ == "__main__":
    import pandas as pd
    demo_futures_trading()