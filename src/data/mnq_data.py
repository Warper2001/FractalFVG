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
    
    # Data quality settings
    min_volume_threshold: int = 100
    max_price_jump_percent: float = 0.5  # Maximum allowed price jump
    fill_missing_data: bool = True
    remove_outliers: bool = True
    
    # Performance settings
    batch_size_days: int = 30
    parallel_processing: bool = True
    memory_limit_mb: int = 1024


class MNQDataAccess:
    """
    Data access layer for MNQ futures historical data.
    
    This class provides comprehensive data retrieval, caching, and processing
    capabilities for MNQ futures data from QuantConnect and local storage.
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


# Utility functions for MNQ data management
def create_sample_mnq_data(start_date: datetime, end_date: datetime,
                          frequency: str = "1min") -> pd.DataFrame:
    """
    Create sample MNQ data for testing purposes.
    
    Args:
        start_date: Start date for sample data
        end_date: End date for sample data
        frequency: Data frequency
        
    Returns:
        DataFrame with sample OHLCV data
    """
    # Create date range
    date_range = pd.date_range(start=start_date, end=end_date, freq=frequency)
    
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
        
        data.append({
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
        
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


def get_contract_months() -> Dict[str, str]:
    """
    Get MNQ contract month codes.
    
    Returns:
        Dictionary mapping month codes to month names
    """
    return {
        'F': 'January',
        'G': 'February',
        'H': 'March',
        'J': 'April',
        'K': 'May',
        'M': 'June',
        'N': 'July',
        'Q': 'August',
        'U': 'September',
        'V': 'October',
        'X': 'November',
        'Z': 'December'
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