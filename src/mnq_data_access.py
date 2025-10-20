"""
MNQ (Micro E-mini Nasdaq-100 Index Futures) Data Access Module for QuantConnect

This module provides comprehensive functionality for accessing and working with MNQ futures data
in QuantConnect LEAN algorithms. It includes methods for subscription, historical data access,
continuous contracts, and contract filtering.

IMPORTANT USAGE NOTE:
This module must be used within a QuantConnect algorithm that imports AlgorithmImports.
Add these lines to your QuantConnect algorithm:

    from AlgorithmImports import *
    from mnq_data_access import MNQDataAccess

Key Features:
- Individual contract subscription
- Continuous contract access
- Contract filtering by expiry
- Historical data retrieval
- Market hours handling
- Data normalization options

Author: FractalFVG Project
Date: 2025-10-20
"""

from typing import List, Dict, Optional, Tuple
from datetime import timedelta, datetime


class MNQDataAccess:
    """
    Comprehensive MNQ futures data access class for QuantConnect algorithms.

    This class encapsulates all MNQ-related data operations including subscription,
    filtering, historical data access, and continuous contract management.

    Note: This class assumes it's being used within a QuantConnect algorithm
    where AlgorithmImports has been imported.
    """

    # MNQ Futures Constants
    CONTRACT_SIZE = 2  # $2 per index point
    TICK_SIZE = 0.25  # Minimum price movement

    def __init__(self, algorithm):
        """
        Initialize MNQ data access with reference to the algorithm.

        Args:
            algorithm: The QuantConnect algorithm instance
        """
        self.algorithm = algorithm
        self._future_symbol = None
        self._continuous_symbol = None
        self._current_contract = None

        # Set MNQ symbol constants (available in QC environment)
        self.MNQ_SYMBOL = Futures.Indices.NASDAQ100Micro
        self.EXCHANGE = Market.CME

    def add_mnq_universe(
        self,
        resolution=None,
        extended_market_hours=True,
        data_normalization_mode=None,
        data_mapping_mode=None,
        contract_depth_offset=0,
        min_expiry_days=0,
        max_expiry_days=182,
    ):
        """
        Add MNQ futures universe with customizable filtering.

        Args:
            resolution: Data resolution (defaults to Resolution.Minute)
            extended_market_hours: Include extended market hours
            data_normalization_mode: How to normalize continuous contract data
            data_mapping_mode: How to map contracts in continuous series
            contract_depth_offset: Offset for contract depth
            min_expiry_days: Minimum days to expiry for filtering
            max_expiry_days: Maximum days to expiry for filtering

        Returns:
            Future object representing the MNQ universe
        """
        # Set defaults using QC constants if not provided
        if resolution is None:
            resolution = Resolution.Minute
        if data_normalization_mode is None:
            data_normalization_mode = DataNormalizationMode.BackwardsRatio
        if data_mapping_mode is None:
            data_mapping_mode = DataMappingMode.OpenInterest

        # Add the future universe
        future = self.algorithm.AddFuture(
            self.MNQ_SYMBOL,
            resolution,
            extendedMarketHours=extended_market_hours,
            dataNormalizationMode=data_normalization_mode,
            dataMappingMode=data_mapping_mode,
            contractDepthOffset=contract_depth_offset,
        )

        # Set filter for contract selection
        future.SetFilter(min_expiry_days, max_expiry_days)

        self._future_symbol = future.Symbol
        self._continuous_symbol = future.Symbol

        self.algorithm.Log(
            f"Added MNQ universe with filter: {min_expiry_days}-{max_expiry_days} days"
        )

        return future

    def add_front_month_mnq(self, resolution=None, extended_market_hours=True):
        """
        Add front-month MNQ contract only.

        Args:
            resolution: Data resolution (defaults to Resolution.Minute)
            extended_market_hours: Include extended market hours

        Returns:
            Future object for front-month MNQ
        """
        future = self.add_mnq_universe(
            resolution=resolution, extended_market_hours=extended_market_hours
        )

        # Override filter to only get front month
        future.SetFilter(lambda universe: universe.FrontMonth())

        self.algorithm.Log("Added front-month MNQ contract")

        return future

    def add_individual_mnq_contract(
        self, contract_symbol, resolution=None, extended_market_hours=True
    ):
        """
        Add a specific MNQ contract by symbol.

        Args:
            contract_symbol: The specific contract symbol to add
            resolution: Data resolution (defaults to Resolution.Minute)
            extended_market_hours: Include extended market hours

        Returns:
            Future object for the specific contract
        """
        if resolution is None:
            resolution = Resolution.Minute

        future = self.algorithm.AddFutureContract(
            contract_symbol, resolution, extendedMarketHours=extended_market_hours
        )

        self._current_contract = contract_symbol
        self.algorithm.Log(f"Added individual MNQ contract: {contract_symbol}")

        return future

    def get_mnq_chain(self):
        """
        Get the current MNQ futures chain.

        Returns:
            FuturesChain object if available, None otherwise
        """
        if self._future_symbol:
            return self.algorithm.FuturesChain(self._future_symbol)
        return None

    def get_front_month_contract(self):
        """
        Get the front-month MNQ contract symbol.

        Returns:
            Symbol of front-month contract if available
        """
        chain = self.get_mnq_chain()
        if chain:
            return list(chain)[0].Symbol  # First contract is front month
        return None

    def get_contracts_by_expiry_range(self, min_days=0, max_days=365):
        """
        Get MNQ contracts within specified expiry range.

        Args:
            min_days: Minimum days to expiry
            max_days: Maximum days to expiry

        Returns:
            List of contract symbols within the range
        """
        chain = self.get_mnq_chain()
        if not chain:
            return []

        current_time = self.algorithm.Time
        target_contracts = []

        for contract in chain:
            days_to_expiry = (contract.Expiry - current_time).days
            if min_days <= days_to_expiry <= max_days:
                target_contracts.append(contract.Symbol)

        return target_contracts

    def get_historical_mnq_data(
        self, start_date, end_date, resolution=None, contract_symbol=None
    ):
        """
        Get historical MNQ data.

        Args:
            start_date: Start date for historical data
            end_date: End date for historical data
            resolution: Data resolution (defaults to Resolution.Minute)
            contract_symbol: Specific contract symbol (uses continuous if None)

        Returns:
            DataFrame with historical OHLCV data
        """
        if resolution is None:
            resolution = Resolution.Minute

        symbol = contract_symbol or self._continuous_symbol

        if not symbol:
            raise ValueError("No MNQ symbol available. Add universe or contract first.")

        history = self.algorithm.History(symbol, start_date, end_date, resolution)

        if history.empty:
            self.algorithm.Log(f"No historical data found for {symbol}")
            # Return empty DataFrame using pandas from QC environment
            return pd.DataFrame()

        # Convert to DataFrame if needed
        if hasattr(history, "empty") and isinstance(history, type(pd.DataFrame())):
            return history
        else:
            # Handle History objects
            data_list = []
            for time, slice_data in history.items():
                if hasattr(slice_data, "close"):
                    data_list.append(
                        {
                            "time": time,
                            "open": slice_data.open,
                            "high": slice_data.high,
                            "low": slice_data.low,
                            "close": slice_data.close,
                            "volume": getattr(slice_data, "volume", 0),
                        }
                    )

            return pd.DataFrame(data_list).set_index("time")

    def get_continuous_price(self):
        """
        Get the current continuous contract price.

        Returns:
            Current price of continuous contract
        """
        if self._continuous_symbol:
            return self.algorithm.Securities[self._continuous_symbol].Price
        return None

    def get_mapped_contract_price(self):
        """
        Get the current mapped contract price (raw price of current contract).

        Returns:
            Current price of mapped contract
        """
        if self._future_symbol:
            future = self.algorithm.Securities[self._future_symbol]
            if hasattr(future, "Mapped"):
                return self.algorithm.Securities[future.Mapped].Price
        return None

    def is_market_open(self):
        """
        Check if MNQ market is currently open.

        Returns:
            True if market is open, False otherwise
        """
        if self._future_symbol:
            return self.algorithm.IsMarketOpen(self._future_symbol)
        return False

    def get_market_hours(self):
        """
        Get MNQ market hours for today.

        Returns:
            Dictionary with market open and close times
        """
        if not self._future_symbol:
            return {}

        exchange_hours = self.algorithm.MarketHoursDatabase.GetExchangeHours(
            self.EXCHANGE, self._future_symbol, self.algorithm.Time
        )

        today_hours = exchange_hours.GetMarketHours(self.algorithm.Time.date())

        return {
            "market_open": today_hours.MarketOpen,
            "market_close": today_hours.MarketClose,
            "pre_market": today_hours.PreMarket,
            "post_market": today_hours.PostMarket,
        }

    def roll_to_front_month(self):
        """
        Roll position to front-month contract.

        Returns:
            True if roll was successful, False otherwise
        """
        front_month = self.get_front_month_contract()
        if not front_month:
            return False

        if self._current_contract != front_month:
            # Liquidate current position if any
            if self._current_contract and self.algorithm.Portfolio.Invested:
                self.algorithm.Liquidate(self._current_contract)

            # Subscribe to new front month
            self.add_individual_mnq_contract(front_month)
            return True

        return False

    def get_contract_expiries(self, days_ahead=365):
        """
        Get upcoming MNQ contract expiries.

        Args:
            days_ahead: Number of days ahead to look for expiries

        Returns:
            List of tuples containing (contract_symbol, expiry_date)
        """
        chain = self.get_mnq_chain()
        if not chain:
            return []

        current_time = self.algorithm.Time
        cutoff_date = current_time + timedelta(days=days_ahead)

        expiries = []
        for contract in chain:
            if contract.Expiry <= cutoff_date:
                expiries.append((contract.Symbol, contract.Expiry))

        return sorted(expiries, key=lambda x: x[1])

    def calculate_contract_value(self, price):
        """
        Calculate the notional value of one MNQ contract.

        Args:
            price: Contract price

        Returns:
            Notional value of one contract
        """
        return price * self.CONTRACT_SIZE

    def get_margin_requirement(self, quantity=1):
        """
        Get margin requirement for MNQ contracts.

        Args:
            quantity: Number of contracts

        Returns:
            Margin requirement amount
        """
        if self._current_contract:
            security = self.algorithm.Securities[self._current_contract]
            return security.BuyingPowerModel.GetRequiredBuyingPower(
                security.PortfolioModel, security, quantity
            ).Value
        return None


# Example algorithm template
EXAMPLE_ALGORITHM_TEMPLATE = '''
from AlgorithmImports import *
from mnq_data_access import MNQDataAccess

class MNQExampleAlgorithm(QCAlgorithm):
    """
    Example algorithm demonstrating MNQ data access usage.
    """
    
    def Initialize(self):
        self.SetStartDate(2024, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100000)
        
        # Initialize MNQ data access
        self.mnq = MNQDataAccess(self)
        
        # Add MNQ universe with front-month filter
        future = self.mnq.add_front_month_mnq(
            resolution=Resolution.Minute,
            extended_market_hours=True
        )
        
        # Create EMA indicator for continuous contract
        self.ema = self.EMA(future.Symbol, 20, Resolution.Daily)
        self.WarmUpIndicator(future.Symbol, self.ema)
        
        # Schedule contract rollover check
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.BeforeMarketClose(future.Symbol, 30),
            self.check_rollover
        )
    
    def OnData(self, data):
        # Get continuous and mapped prices
        continuous_price = self.mnq.get_continuous_price()
        mapped_price = self.mnq.get_mapped_contract_price()
        
        if continuous_price and mapped_price:
            # Simple EMA crossover strategy
            if continuous_price > self.ema.Current.Value and not self.Portfolio.Invested:
                self.MarketOrder(self.mnq._future_symbol, 1)
            elif continuous_price < self.ema.Current.Value and self.Portfolio.Invested:
                self.Liquidate()
    
    def check_rollover(self):
        # Check if we need to roll to new front month
        if self.mnq.roll_to_front_month():
            self.Log("Rolled to new front-month contract")
'''
