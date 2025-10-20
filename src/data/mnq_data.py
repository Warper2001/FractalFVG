"""
Data access layer for MNQ (Micro E-mini Nasdaq-100) historical data.

This module provides comprehensive data access capabilities for MNQ futures data,
including retrieval from QuantConnect, local storage management, and multi-timeframe
data preparation for FVG confluence analysis.
"""

from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
import os
import json
from dataclasses import dataclass, asdict

# QuantConnect imports (these will be available in LEAN environment)
try:
    from AlgorithmImports import QCAlgorithm, Resolution, HistoryRequest, TickType, DataNormalizationMode
    from QuantConnect.Data import SubscriptionDataSource
    from QuantConnect.Interfaces import IDataProvider
    from QuantConnect.Python import PythonData
except ImportError:
    # Mock classes for development/testing outside LEAN
    class QCAlgorithm:
        pass
    
    class Resolution:
        Tick = "tick"
        Second = "second"
        Minute = "minute"
        Hour = "hour"
        Daily = "daily"
    
    class HistoryRequest:
        pass
    
    class TickType:
        Trade = "trade"
        Quote = "quote"
        OpenInterest = "open_interest"
    
    class DataNormalizationMode:
        Raw = "raw"
        SplitAdjusted = "split_adjusted"
        TotalReturn = "total_return"
    
    class SubscriptionDataSource:
        pass
    
    class IDataProvider:
        pass
    
    class PythonData:
        pass


@dataclass
class MNQDataConfig:
    """Configuration for MNQ data access."""
    symbol: str = "MNQ"
    exchange: str = "CME"
    data_directory: str = "data/mnq"
    cache_duration_hours: int = 24
    max_data_age_days: int = 730  # 2 years
    enable_local_cache: bool = True
    enable_quantconnect: bool = True
    resolution: str = "minute"
    tick_type: str = "trade"
    normalization_mode: str = "raw"
    
    # Contract rolling settings
    enable_contract_rolling: bool = True
    roll_days_before_expiry: int = 5  # Roll 5 days before expiry
    roll_method: str = "ratio"  # "ratio", "difference", or "raw"
    continuous_contract_symbol: str = "MNQ"  # Symbol for continuous contract
    
    # Data quality settings
    min_volume_threshold: int = 100
    max_price_jump_percent: float = 0.5  # Maximum allowed price jump
    fill_missing_data: bool = True
    remove_outliers: bool = True
    
    # Performance settings
    batch_size_days: int = 30
    parallel_processing: bool = True
    memory_limit_mb: int = 1024


@dataclass
class FuturesContract:
    """Futures contract information."""
    symbol: str
    contract_month: str
    expiry_date: datetime
    first_notice_date: Optional[datetime] = None
    roll_date: Optional[datetime] = None
    
    def get_full_symbol(self) -> str:
        """Get the full futures symbol (e.g., MNQH24)."""
        return f"{self.symbol}{self.contract_month}"
        
    def is_expired(self, current_date: datetime) -> bool:
        """Check if contract is expired."""
        return current_date >= self.expiry_date
        
    def should_roll(self, current_date: datetime, roll_days_before: int) -> bool:
        """Check if contract should be rolled."""
        if self.roll_date:
            return current_date >= self.roll_date
        else:
            roll_date = self.expiry_date - timedelta(days=roll_days_before)
            return current_date >= roll_date


class MNQDataAccess:
    """
    Data access layer for MNQ futures historical data.
    
    This class provides comprehensive data retrieval, caching, and processing
    capabilities for MNQ futures data from QuantConnect and local storage,
    including proper contract rolling for continuous data series.
    """
    
    def __init__(self, config: Optional[MNQDataConfig] = None):
        """
        Initialize MNQ data access layer.
        
        Args:
            config: Configuration for data access
        """
        self.config = config or MNQDataConfig()
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.contract_cache: Dict[str, FuturesContract] = {}
        
        # Ensure data directory exists
        if self.config.enable_local_cache:
            Path(self.config.data_directory).mkdir(parents=True, exist_ok=True)
            
    def get_historical_data(self, start_date: datetime, end_date: datetime,
                          resolution: str = "minute") -> pd.DataFrame:
        """
        Get historical MNQ data for the specified date range.
        
        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            resolution: Data resolution (tick, second, minute, hour, daily)
            
        Returns:
            DataFrame with OHLCV data
        """
        # Check cache first
        cache_key = f"{self.config.symbol}_{start_date.date()}_{end_date.date()}_{resolution}"
        
        if self._is_cache_valid(cache_key):
            return self.data_cache[cache_key].copy()
            
        # If contract rolling is enabled, get continuous contract data
        if self.config.enable_contract_rolling:
            continuous_data = self._get_continuous_contract_data(start_date, end_date, resolution)
            if continuous_data is not None:
                self._cache_data(cache_key, continuous_data)
                return continuous_data
        
        # Try to load from local storage
        local_data = self._load_from_local_storage(start_date, end_date, resolution)
        if local_data is not None:
            self._cache_data(cache_key, local_data)
            return local_data
            
        # Fetch from QuantConnect
        if self.config.enable_quantconnect:
            qc_data = self._fetch_from_quantconnect(start_date, end_date, resolution)
            if qc_data is not None:
                # Process and clean the data
                processed_data = self._process_data(qc_data)
                
                # Save to local cache
                if self.config.enable_local_cache:
                    self._save_to_local_storage(processed_data, start_date, end_date, resolution)
                    
                self._cache_data(cache_key, processed_data)
                return processed_data
                
        raise ValueError(f"Unable to retrieve MNQ data for {start_date.date()} to {end_date.date()}")
        
    def get_multi_timeframe_data(self, start_date: datetime, end_date: datetime,
                               timeframes: List[int]) -> Dict[int, pd.DataFrame]:
        """
        Get MNQ data for multiple timeframes.
        
        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            timeframes: List of timeframes in minutes
            
        Returns:
            Dictionary of DataFrames by timeframe
        """
        # Get base minute data
        minute_data = self.get_historical_data(start_date, end_date, "minute")
        
        # Generate data for each timeframe
        timeframe_data = {}
        
        for timeframe in timeframes:
            if timeframe == 1:
                timeframe_data[timeframe] = minute_data.copy()
            else:
                timeframe_data[timeframe] = self._resample_data(minute_data, timeframe)
                
        return timeframe_data
        
    def get_latest_data(self, minutes: int = 60) -> pd.DataFrame:
        """
        Get the latest MNQ data.
        
        Args:
            minutes: Number of minutes of latest data to retrieve
            
        Returns:
            DataFrame with latest OHLCV data
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=minutes)
        
        return self.get_historical_data(start_time, end_time, "minute")
        
    def validate_data_quality(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate the quality of MNQ data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for missing data
        if df.isnull().any().any():
            missing_cols = df.columns[df.isnull().any()].tolist()
            issues.append(f"Missing data in columns: {missing_cols}")
            
        # Check for duplicate timestamps
        if df.index.duplicated().any():
            issues.append("Duplicate timestamps found")
            
        # Check for price anomalies
        if 'close' in df.columns:
            price_changes = df['close'].pct_change().abs()
            large_changes = price_changes[price_changes > self.config.max_price_jump_percent / 100]
            if not large_changes.empty:
                issues.append(f"Found {len(large_changes)} large price jumps (> {self.config.max_price_jump_percent}%)")
                
        # Check volume
        if 'volume' in df.columns:
            low_volume = df[df['volume'] < self.config.min_volume_threshold]
            if not low_volume.empty:
                issues.append(f"Found {len(low_volume)} low volume periods (< {self.config.min_volume_threshold})")
                
        # Check for negative prices
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in df.columns and (df[col] <= 0).any():
                issues.append(f"Found non-positive {col} prices")
                
        # Check OHLC consistency
        if all(col in df.columns for col in price_cols):
            invalid_ohlc = (df['high'] < df['low']) | (df['high'] < df['open']) | (df['high'] < df['close']) | \
                          (df['low'] > df['open']) | (df['low'] > df['close'])
            if invalid_ohlc.any():
                issues.append("Found invalid OHLC relationships")
                
        return len(issues) == 0, issues
        
    def get_data_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Get comprehensive statistics for MNQ data.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dictionary with data statistics
        """
        stats = {
            'total_records': len(df),
            'date_range': {
                'start': df.index.min().isoformat() if not df.empty else None,
                'end': df.index.max().isoformat() if not df.empty else None
            },
            'price_stats': {},
            'volume_stats': {},
            'data_quality': {}
        }
        
        if not df.empty:
            # Price statistics
            price_cols = ['open', 'high', 'low', 'close']
            for col in price_cols:
                if col in df.columns:
                    stats['price_stats'][col] = {
                        'min': float(df[col].min()),
                        'max': float(df[col].max()),
                        'mean': float(df[col].mean()),
                        'std': float(df[col].std()),
                        'median': float(df[col].median())
                    }
                    
            # Volume statistics
            if 'volume' in df.columns:
                stats['volume_stats'] = {
                    'min': int(df['volume'].min()),
                    'max': int(df['volume'].max()),
                    'mean': float(df['volume'].mean()),
                    'std': float(df['volume'].std()),
                    'median': float(df['volume'].median()),
                    'total': int(df['volume'].sum())
                }
                
            # Data quality
            is_valid, issues = self.validate_data_quality(df)
            stats['data_quality'] = {
                'is_valid': is_valid,
                'issues': issues,
                'missing_data_pct': float(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100)
            }
            
        return stats
        
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.data_cache:
            return False
            
        if cache_key not in self.cache_timestamps:
            return False
            
        age = datetime.now() - self.cache_timestamps[cache_key]
        return age.total_seconds() < self.config.cache_duration_hours * 3600
        
    def _cache_data(self, cache_key: str, data: pd.DataFrame) -> None:
        """Cache data with timestamp."""
        self.data_cache[cache_key] = data.copy()
        self.cache_timestamps[cache_key] = datetime.now()
        
        # Clean old cache entries
        self._clean_old_cache()
        
    def _clean_old_cache(self) -> None:
        """Remove old cache entries."""
        current_time = datetime.now()
        expired_keys = []
        
        for key, timestamp in self.cache_timestamps.items():
            age = current_time - timestamp
            if age.total_seconds() > self.config.cache_duration_hours * 3600:
                expired_keys.append(key)
                
        for key in expired_keys:
            self.data_cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
            
    def _load_from_local_storage(self, start_date: datetime, end_date: datetime,
                               resolution: str) -> Optional[pd.DataFrame]:
        """Load data from local storage."""
        if not self.config.enable_local_cache:
            return None
            
        filename = self._get_local_filename(start_date, end_date, resolution)
        filepath = Path(self.config.data_directory) / filename
        
        if not filepath.exists():
            return None
            
        try:
            # Load parquet file (preferred format)
            if filepath.suffix == '.parquet':
                df = pd.read_parquet(filepath)
            # Load CSV file
            elif filepath.suffix == '.csv':
                df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            else:
                return None
                
            # Validate data
            is_valid, issues = self.validate_data_quality(df)
            if not is_valid:
                print(f"Data quality issues in {filename}: {issues}")
                
            return df
            
        except Exception as e:
            print(f"Error loading local data from {filename}: {e}")
            return None
            
    def _save_to_local_storage(self, df: pd.DataFrame, start_date: datetime,
                             end_date: datetime, resolution: str) -> None:
        """Save data to local storage."""
        if not self.config.enable_local_cache:
            return
            
        filename = self._get_local_filename(start_date, end_date, resolution)
        filepath = Path(self.config.data_directory) / filename
        
        try:
            # Save as parquet (preferred format)
            filepath = filepath.with_suffix('.parquet')
            df.to_parquet(filepath, compression='snappy')
            
            # Also save metadata
            metadata = {
                'symbol': self.config.symbol,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'resolution': resolution,
                'records': len(df),
                'created_at': datetime.now().isoformat()
            }
            
            metadata_file = filepath.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            print(f"Error saving local data to {filename}: {e}")
            
    def _get_local_filename(self, start_date: datetime, end_date: datetime,
                          resolution: str) -> str:
        """Generate local storage filename."""
        return f"{self.config.symbol}_{start_date.date()}_{end_date.date()}_{resolution}"
        
    def _fetch_from_quantconnect(self, start_date: datetime, end_date: datetime,
                               resolution: str) -> Optional[pd.DataFrame]:
        """Fetch data from QuantConnect."""
        try:
            # This would be implemented in the actual QuantConnect environment
            # For now, return None to indicate no data available
            print(f"Would fetch from QuantConnect: {start_date.date()} to {end_date.date()} at {resolution}")
            return None
            
        except Exception as e:
            print(f"Error fetching from QuantConnect: {e}")
            return None
            
    def _process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and clean raw data."""
        if df.empty:
            return df
            
        processed_df = df.copy()
        
        # Remove outliers if enabled
        if self.config.remove_outliers:
            processed_df = self._remove_outliers(processed_df)
            
        # Fill missing data if enabled
        if self.config.fill_missing_data:
            processed_df = self._fill_missing_data(processed_df)
            
        # Ensure proper data types
        processed_df = self._ensure_data_types(processed_df)
        
        # Sort by index
        processed_df = processed_df.sort_index()
        
        return processed_df
        
    def _remove_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove outliers from the data."""
        # Remove extreme price movements
        if 'close' in df.columns:
            price_changes = df['close'].pct_change().abs()
            outlier_mask = price_changes > self.config.max_price_jump_percent / 100
            
            # Replace outliers with forward fill
            df.loc[outlier_mask, ['open', 'high', 'low', 'close']] = np.nan
            
        return df
        
    def _fill_missing_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fill missing data using appropriate methods."""
        # Forward fill for price data
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in df.columns:
                df[col] = df[col].ffill()
                
        # Fill volume with 0 for missing data
        if 'volume' in df.columns:
            df['volume'] = df['volume'].fillna(0)
            
        return df
        
    def _ensure_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure proper data types."""
        # Convert price columns to float
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        # Convert volume to integer
        if 'volume' in df.columns:
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)
            
        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            
        return df
        
    def _resample_data(self, df: pd.DataFrame, timeframe_minutes: int) -> pd.DataFrame:
        """Resample data to a different timeframe."""
        if df.empty:
            return df
            
        # Define resampling rule
        rule = f"{timeframe_minutes}min"
        
        # Resample OHLCV data
        resampled = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # Remove rows with missing data
        resampled = resampled.dropna()
        
        return resampled
        
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.data_cache.clear()
        self.cache_timestamps.clear()
        
    def get_cache_info(self) -> Dict:
        """Get information about cached data."""
        total_memory = sum(df.memory_usage(deep=True).sum() for df in self.data_cache.values())
        
        return {
            'cached_items': len(self.data_cache),
            'total_memory_mb': total_memory / (1024 * 1024),
            'cache_keys': list(self.data_cache.keys()),
            'oldest_cache': min(self.cache_timestamps.values()) if self.cache_timestamps else None,
            'newest_cache': max(self.cache_timestamps.values()) if self.cache_timestamps else None
        }
        
    def _get_continuous_contract_data(self, start_date: datetime, end_date: datetime,
                                    resolution: str) -> Optional[pd.DataFrame]:
        """
        Get continuous contract data with proper rolling.
        
        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            resolution: Data resolution
            
        Returns:
            DataFrame with continuous contract data
        """
        # Get contract series for the date range
        contracts = self._get_contract_series(start_date, end_date)
        
        if not contracts:
            return None
            
        # Get data for each contract
        contract_data_list = []
        
        for i, contract in enumerate(contracts):
            # Determine date range for this contract
            contract_start = max(start_date, contract.roll_date or start_date)
            contract_end = min(end_date, contract.expiry_date)
            
            if contract_start >= contract_end:
                continue
                
            # Get data for this specific contract
            contract_symbol = contract.get_full_symbol()
            try:
                contract_data = self._get_single_contract_data(
                    contract_symbol, contract_start, contract_end, resolution
                )
                
                if contract_data is not None and not contract_data.empty:
                    # Apply rolling adjustments if not the first contract
                    if i > 0 and self.config.roll_method != "raw":
                        contract_data = self._apply_rolling_adjustment(
                            contract_data, contracts[i-1], contract
                        )
                    
                    contract_data_list.append(contract_data)
                    
            except Exception as e:
                print(f"Error getting data for {contract_symbol}: {e}")
                continue
                
        if not contract_data_list:
            return None
            
        # Combine all contract data
        continuous_data = pd.concat(contract_data_list, ignore_index=False)
        continuous_data = continuous_data.sort_index()
        
        # Remove any duplicates
        continuous_data = continuous_data[~continuous_data.index.duplicated(keep='first')]
        
        return continuous_data
        
    def _get_contract_series(self, start_date: datetime, end_date: datetime) -> List[FuturesContract]:
        """
        Get the series of contracts for the given date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of contracts in chronological order
        """
        contracts = []
        current_date = start_date
        
        # Generate contract months (MNQ trades quarterly: H, M, U, Z)
        contract_months = ['H', 'M', 'U', 'Z']  # March, June, September, December
        
        year = current_date.year
        month = current_date.month
        
        # Find the next contract month
        while current_date <= end_date:
            # Find the next contract month
            for month_code in contract_months:
                month_number = get_contract_months()[month_code]
                contract_date = datetime(year, month_number, 1)
                
                # Generate expiry date (3rd Friday of the month for MNQ)
                expiry_date = self._get_third_friday(year, month_number)
                
                # Create contract
                contract = FuturesContract(
                    symbol=self.config.symbol,
                    contract_month=f"{month_code}{str(year)[-2:]}",
                    expiry_date=expiry_date,
                    roll_date=expiry_date - timedelta(days=self.config.roll_days_before_expiry)
                )
                
                # Check if this contract is relevant for our date range
                if contract.roll_date <= end_date and contract.expiry_date >= start_date:
                    contracts.append(contract)
                    
                # Move to next quarter
                if month_number >= 12:
                    year += 1
                    break
                    
            current_date = datetime(year, month_number + 3, 1)
            
        return contracts
        
    def _get_third_friday(self, year: int, month: int) -> datetime:
        """
        Calculate the third Friday of a given month and year.
        
        Args:
            year: Year
            month: Month
            
        Returns:
            Third Friday datetime
        """
        # Find the first day of the month
        first_day = datetime(year, month, 1)
        
        # Find the first Friday
        days_until_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_until_friday)
        
        # Add 14 days to get the third Friday
        third_friday = first_friday + timedelta(days=14)
        
        return third_friday
        
    def _get_single_contract_data(self, symbol: str, start_date: datetime, 
                                end_date: datetime, resolution: str) -> Optional[pd.DataFrame]:
        """
        Get data for a single futures contract.
        
        Args:
            symbol: Contract symbol (e.g., MNQH24)
            start_date: Start date
            end_date: End date
            resolution: Data resolution
            
        Returns:
            DataFrame with contract data
        """
        # Check cache first
        cache_key = f"{symbol}_{start_date.date()}_{end_date.date()}_{resolution}"
        
        if self._is_cache_valid(cache_key):
            return self.data_cache[cache_key].copy()
            
        # Try to load from local storage
        local_data = self._load_from_local_storage(start_date, end_date, resolution, symbol)
        if local_data is not None:
            self._cache_data(cache_key, local_data)
            return local_data
            
        # Fetch from QuantConnect
        if self.config.enable_quantconnect:
            qc_data = self._fetch_contract_from_quantconnect(symbol, start_date, end_date, resolution)
            if qc_data is not None:
                processed_data = self._process_data(qc_data)
                
                # Save to local cache
                if self.config.enable_local_cache:
                    self._save_to_local_storage(processed_data, start_date, end_date, resolution, symbol)
                    
                self._cache_data(cache_key, processed_data)
                return processed_data
                
        return None
        
    def _apply_rolling_adjustment(self, new_contract_data: pd.DataFrame,
                                old_contract: FuturesContract, 
                                new_contract: FuturesContract) -> pd.DataFrame:
        """
        Apply rolling adjustment to new contract data.
        
        Args:
            new_contract_data: Data for the new contract
            old_contract: Previous contract
            new_contract: New contract
            
        Returns:
            Adjusted contract data
        """
        if self.config.roll_method == "raw":
            return new_contract_data
            
        # Get overlapping data for ratio calculation
        overlap_start = new_contract.roll_date
        overlap_end = min(new_contract.expiry_date, overlap_start + timedelta(days=5))
        
        # For this implementation, we'll use a simple adjustment factor
        # In practice, you'd calculate this from actual overlapping data
        adjustment_factor = 1.0  # Placeholder
        
        if self.config.roll_method == "ratio":
            # Apply ratio adjustment
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in new_contract_data.columns:
                    new_contract_data[col] = new_contract_data[col] * adjustment_factor
                    
        elif self.config.roll_method == "difference":
            # Apply difference adjustment
            adjustment_amount = 0.0  # Placeholder
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in new_contract_data.columns:
                    new_contract_data[col] = new_contract_data[col] + adjustment_amount
                    
        return new_contract_data
        
    def _fetch_contract_from_quantconnect(self, symbol: str, start_date: datetime,
                                       end_date: datetime, resolution: str) -> Optional[pd.DataFrame]:
        """
        Fetch specific contract data from QuantConnect.
        
        Args:
            symbol: Contract symbol
            start_date: Start date
            end_date: End date
            resolution: Data resolution
            
        Returns:
            DataFrame with contract data
        """
        try:
            # This would be implemented in the actual QuantConnect environment
            print(f"Would fetch {symbol} from QuantConnect: {start_date.date()} to {end_date.date()} at {resolution}")
            return None
            
        except Exception as e:
            print(f"Error fetching {symbol} from QuantConnect: {e}")
            return None


# Utility functions for MNQ data management
def create_sample_mnq_data(start_date: datetime, end_date: datetime,
                          frequency: str = "1min", 
                          include_contracts: bool = True) -> pd.DataFrame:
    """
    Create sample MNQ data for testing purposes.
    
    Args:
        start_date: Start date for sample data
        end_date: End date for sample data
        frequency: Data frequency
        include_contracts: Whether to include contract rolling information
        
    Returns:
        DataFrame with sample OHLCV data
    """
    # Create date range
    # Convert frequency string to pandas format
    freq_map = {
        "1min": "1min", "5min": "5min", "15min": "15min", "30min": "30min",
        "1hour": "1h", "4hour": "4h", "1day": "1D"
    }
    pandas_freq = freq_map.get(frequency, "1h")  # Default to 1h
    date_range = pd.date_range(start=start_date, end=end_date, freq=pandas_freq)
    
    # Filter for trading hours (9:30 AM - 4:00 PM EST, Monday-Friday)
    trading_hours = date_range[
        (date_range.hour >= 9) & (date_range.hour < 16) &
        (date_range.dayofweek < 5)  # Monday-Friday
    ]
    
    if len(trading_hours) == 0:
        return pd.DataFrame()
        
    # Generate realistic price data
    np.random.seed(42)  # For reproducible data
    
    # Starting price around 15000 for MNQ
    initial_price = 15000.0
    price_changes = np.random.normal(0, 5, len(trading_hours))  # Small random changes
    prices = initial_price + np.cumsum(price_changes)
    
    # Add some volatility
    volatility = np.random.uniform(10, 50, len(trading_hours))
    
    # Generate contract information if requested
    contracts = []
    if include_contracts:
        contracts = generate_mnq_contracts(start_date.year, end_date.year)
    
    # Generate OHLC data
    data = []
    for i, (timestamp, close_price) in enumerate(zip(trading_hours, prices)):
        vol = volatility[i]
        
        # Generate realistic OHLC
        if i == 0:
            open_price = close_price
        else:
            open_price = data[-1]['close']
            
        # Ensure OHLC relationships are valid
        high_price = max(open_price, close_price) + np.random.uniform(0, vol)
        low_price = min(open_price, close_price) - np.random.uniform(0, vol)
        
        # Generate volume (higher during active hours)
        base_volume = 1000
        hour_multiplier = 1.5 if 10 <= timestamp.hour <= 14 else 1.0
        volume = int(base_volume * hour_multiplier * np.random.uniform(0.5, 2.0))
        
        row_data = {
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        }
        
        # Add contract information if requested
        if include_contracts:
            current_contract = None
            for contract in contracts:
                if not contract.is_expired(timestamp) and not contract.should_roll(timestamp, 5):
                    current_contract = contract.get_full_symbol()
                    break
                    
            row_data['contract'] = current_contract or 'MNQ'
            
        data.append(row_data)
        
    df = pd.DataFrame(data, index=trading_hours)
    return df


def validate_mnq_symbol(symbol: str) -> bool:
    """
    Validate MNQ symbol format.
    
    Args:
        symbol: Symbol to validate
        
    Returns:
        True if symbol is valid MNQ format
    """
    # MNQ symbols typically follow patterns like:
    # MNQ, MNQH24, MNQM24, MNQU24, MNQZ24 (for different contract months)
    valid_patterns = [
        r'^MNQ$',  # Continuous contract
        r'^MNQ[HJKMNQUVZ]\d{2}$'  # Monthly contracts
    ]
    
    import re
    return any(re.match(pattern, symbol.upper()) for pattern in valid_patterns)


def get_contract_months() -> Dict[str, int]:
    """
    Get MNQ contract month codes.
    
    Returns:
        Dictionary mapping month codes to month numbers
    """
    return {
        'F': 1,
        'G': 2,
        'H': 3,
        'J': 4,
        'K': 5,
        'M': 6,
        'N': 7,
        'Q': 8,
        'U': 9,
        'V': 10,
        'X': 11,
        'Z': 12
    }


def get_trading_hours() -> Dict[str, Tuple[int, int]]:
    """
    Get MNQ trading hours by session.
    
    Returns:
        Dictionary mapping session names to (start_hour, end_hour)
    """
    return {
        'pre_market': (4, 9),      # 4:00 AM - 9:30 AM EST
        'regular': (9, 16),        # 9:30 AM - 4:00 PM EST
        'after_hours': (16, 20),   # 4:00 PM - 8:00 PM EST
        'overnight': (20, 24)      # 8:00 PM - 12:00 AM EST
    }


def generate_mnq_contracts(start_year: int, end_year: int) -> List[FuturesContract]:
    """
    Generate MNQ futures contracts for a range of years.
    
    Args:
        start_year: Starting year
        end_year: Ending year
        
    Returns:
        List of MNQ futures contracts
    """
    contracts = []
    contract_months = ['H', 'M', 'U', 'Z']  # March, June, September, December
    month_mapping = get_contract_months()
    
    for year in range(start_year, end_year + 1):
        for month_code in contract_months:
            month_number = month_mapping[month_code]
            expiry_date = get_third_friday(year, month_number)
            
            contract = FuturesContract(
                symbol="MNQ",
                contract_month=f"{month_code}{str(year)[-2:]}",
                expiry_date=expiry_date,
                roll_date=expiry_date - timedelta(days=5)  # Roll 5 days before expiry
            )
            contracts.append(contract)
            
    return contracts


def get_third_friday(year: int, month: int) -> datetime:
    """
    Calculate the third Friday of a given month and year.
    
    Args:
        year: Year
        month: Month
        
    Returns:
        Third Friday datetime
    """
    # Find the first day of the month
    first_day = datetime(year, month, 1)
    
    # Find the first Friday
    days_until_friday = (4 - first_day.weekday()) % 7
    first_friday = first_day + timedelta(days=days_until_friday)
    
    # Add 14 days to get the third Friday
    third_friday = first_friday + timedelta(days=14)
    
    return third_friday


def calculate_rolling_ratio(old_price: float, new_price: float) -> float:
    """
    Calculate rolling ratio for contract adjustment.
    
    Args:
        old_price: Price of old contract
        new_price: Price of new contract
        
    Returns:
        Rolling ratio
    """
    if old_price == 0:
        return 1.0
    return new_price / old_price


def calculate_rolling_difference(old_price: float, new_price: float) -> float:
    """
    Calculate rolling difference for contract adjustment.
    
    Args:
        old_price: Price of old contract
        new_price: Price of new contract
        
    Returns:
        Rolling difference
    """
    return new_price - old_price


def get_current_mnq_contract(current_date: Optional[datetime] = None) -> Optional[FuturesContract]:
    """
    Get the current active MNQ contract.
    
    Args:
        current_date: Current date (defaults to now)
        
    Returns:
        Current active contract or None
    """
    if current_date is None:
        current_date = datetime.now()
        
    # Generate contracts for the current and next year
    contracts = generate_mnq_contracts(current_date.year, current_date.year + 1)
    
    # Find the contract that's currently active
    for contract in contracts:
        if not contract.is_expired(current_date) and not contract.should_roll(
            current_date, 5  # 5 days before expiry
        ):
            return contract
            
    return None


def get_next_mnq_contract(current_date: Optional[datetime] = None) -> Optional[FuturesContract]:
    """
    Get the next MNQ contract (the one to roll into).
    
    Args:
        current_date: Current date (defaults to now)
        
    Returns:
        Next contract or None
    """
    if current_date is None:
        current_date = datetime.now()
        
    # Generate contracts for the current and next year
    contracts = generate_mnq_contracts(current_date.year, current_date.year + 1)
    
    # Find the current contract first
    current_contract = get_current_mnq_contract(current_date)
    
    if current_contract is None:
        return None
        
    # Find the next contract in the series
    for i, contract in enumerate(contracts):
        if contract.contract_month == current_contract.contract_month:
            if i + 1 < len(contracts):
                return contracts[i + 1]
            break
            
    return None


def create_continuous_contract_data(contracts: List[FuturesContract], 
                                 data_getter: callable) -> pd.DataFrame:
    """
    Create continuous contract data from individual contracts.
    
    Args:
        contracts: List of contracts in chronological order
        data_getter: Function to get data for a contract (symbol, start, end) -> DataFrame
        
    Returns:
        Continuous contract DataFrame
    """
    if not contracts:
        return pd.DataFrame()
        
    contract_data_list = []
    
    for i, contract in enumerate(contracts):
        # Get data for this contract
        start_date = contract.roll_date or contract.expiry_date - timedelta(days=30)
        end_date = contract.expiry_date
        
        try:
            contract_data = data_getter(contract.get_full_symbol(), start_date, end_date)
            
            if contract_data is not None and not contract_data.empty:
                # Apply rolling adjustments if not the first contract
                if i > 0:
                    # Calculate adjustment factor from overlapping period
                    adjustment_factor = calculate_adjustment_factor(
                        contract_data_list[-1], contract_data
                    )
                    contract_data = apply_adjustment(contract_data, adjustment_factor)
                    
                contract_data_list.append(contract_data)
                
        except Exception as e:
            print(f"Error getting data for {contract.get_full_symbol()}: {e}")
            continue
            
    if not contract_data_list:
        return pd.DataFrame()
        
    # Combine all contract data
    continuous_data = pd.concat(contract_data_list, ignore_index=False)
    continuous_data = continuous_data.sort_index()
    
    # Remove duplicates
    continuous_data = continuous_data[~continuous_data.index.duplicated(keep='first')]
    
    return continuous_data


def calculate_adjustment_factor(old_data: pd.DataFrame, new_data: pd.DataFrame) -> float:
    """
    Calculate adjustment factor for contract rolling.
    
    Args:
        old_data: Data from old contract
        new_data: Data from new contract
        
    Returns:
        Adjustment factor
    """
    # Find overlapping period
    overlap_start = max(old_data.index.min(), new_data.index.min())
    overlap_end = min(old_data.index.max(), new_data.index.max())
    
    if overlap_start >= overlap_end:
        return 1.0  # No overlap, use default
        
    # Get overlapping data
    old_overlap = old_data.loc[overlap_start:overlap_end]
    new_overlap = new_data.loc[overlap_start:overlap_end]
    
    if old_overlap.empty or new_overlap.empty:
        return 1.0
        
    # Calculate ratio using closing prices
    old_close = old_overlap['close'].mean()
    new_close = new_overlap['close'].mean()
    
    if old_close == 0:
        return 1.0
        
    return new_close / old_close


def apply_adjustment(data: pd.DataFrame, adjustment_factor: float) -> pd.DataFrame:
    """
    Apply adjustment factor to contract data.
    
    Args:
        data: Contract data
        adjustment_factor: Adjustment factor
        
    Returns:
        Adjusted data
    """
    adjusted_data = data.copy()
    
    # Apply to price columns
    price_columns = ['open', 'high', 'low', 'close']
    for col in price_columns:
        if col in adjusted_data.columns:
            adjusted_data[col] = adjusted_data[col] * adjustment_factor
            
    return adjusted_data