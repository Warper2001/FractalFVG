"""
Base indicator class for FVG strategy with QuantConnect compatibility.

This module provides the foundation for all custom indicators used in the FVG
Confluence Trading Strategy, with proper handling for development and production environments.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Mock QuantConnect classes for development
class MockPythonIndicator:
    """Mock PythonIndicator for development outside QuantConnect."""
    def __init__(self):
        self.Value = 0.0
        self.Time = datetime.now()
        self.IsReady = False
        self.Samples = 0
        
    def Update(self, input_data):
        return False

# Try to import QuantConnect, use mock if not available
try:
    from AlgorithmImports import PythonIndicator
    HAS_QUANTCONNECT = True
except ImportError:
    PythonIndicator = MockPythonIndicator
    HAS_QUANTCONNECT = False


class FVGBaseIndicator(PythonIndicator):
    """
    Base class for FVG-related indicators.
    
    This class provides common functionality for all FVG strategy indicators,
    including data validation, time tracking, and performance monitoring.
    """
    
    def __init__(self, name: str, timeframe: int = 1):
        """
        Initialize the base FVG indicator.
        
        Args:
            name: Indicator name for identification
            timeframe: Timeframe in minutes for this indicator
        """
        super().__init__()
        
        # Indicator identification
        self.name = name
        self.timeframe = timeframe
        self.indicator_type = "FVG_BASE"
        
        # Data storage
        self.price_data: pd.DataFrame = pd.DataFrame()
        self.volume_data: List[float] = []
        self.indicator_data: Dict[str, Any] = {}
        
        # Configuration
        self.max_bars = 1000  # Maximum bars to keep in memory
        self.min_bars = 3      # Minimum bars required for calculation
        
        # State tracking
        self.last_update_time: Optional[datetime] = None
        self.update_count: int = 0
        
        # Performance tracking
        self.calculation_times: List[float] = []
        
    def _validate_input_data(self, input_data: Any) -> bool:
        """
        Validate input data before processing.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        if input_data is None:
            return False
            
        # Handle different input types
        if hasattr(input_data, 'Value') and hasattr(input_data, 'Time'):
            # QuantConnect data format
            if input_data.Value <= 0:
                return False
            return True
        elif isinstance(input_data, dict):
            # Dictionary format
            required_fields = ['open', 'high', 'low', 'close', 'volume']
            return all(field in input_data for field in required_fields)
        elif isinstance(input_data, pd.Series):
            # Pandas Series format
            required_fields = ['open', 'high', 'low', 'close', 'volume']
            return all(field in input_data.index for field in required_fields)
            
        return False
        
    def _extract_price_data(self, input_data: Any) -> Optional[Dict[str, Any]]:
        """
        Extract price data from input in various formats.
        
        Args:
            input_data: Input data to extract prices from
            
        Returns:
            Dictionary with OHLCV data or None if extraction fails
        """
        try:
            if hasattr(input_data, 'Value') and hasattr(input_data, 'Time'):
                # QuantConnect format - single price value
                return {
                    'close': float(input_data.Value),
                    'open': float(input_data.Value),
                    'high': float(input_data.Value),
                    'low': float(input_data.Value),
                    'volume': 0.0,
                    'time': input_data.Time
                }
            elif isinstance(input_data, dict):
                return {
                    'open': float(input_data['open']),
                    'high': float(input_data['high']),
                    'low': float(input_data['low']),
                    'close': float(input_data['close']),
                    'volume': float(input_data.get('volume', 0)),
                    'time': input_data.get('time', datetime.now())
                }
            elif isinstance(input_data, pd.Series):
                return {
                    'open': float(input_data['open']),
                    'high': float(input_data['high']),
                    'low': float(input_data['low']),
                    'close': float(input_data['close']),
                    'volume': float(input_data.get('volume', 0)),
                    'time': input_data.get('time', datetime.now())
                }
        except (KeyError, ValueError, TypeError) as e:
            self._log_error(f"Error extracting price data: {e}")
            
        return None
        
    def _add_price_bar(self, price_data: Dict[str, Any]) -> None:
        """
        Add a new price bar to the indicator's data storage.
        
        Args:
            price_data: Dictionary with OHLCV data
        """
        # Create new row
        new_row = pd.DataFrame([{
            'time': price_data['time'],
            'open': price_data['open'],
            'high': price_data['high'],
            'low': price_data['low'],
            'close': price_data['close'],
            'volume': price_data['volume']
        }])
        
        # Append to existing data
        if self.price_data.empty:
            self.price_data = new_row
        else:
            self.price_data = pd.concat([self.price_data, new_row], ignore_index=True)
            
        # Maintain maximum bars limit
        if len(self.price_data) > self.max_bars:
            self.price_data = self.price_data.tail(self.max_bars).reset_index(drop=True)
            
        # Update volume data
        if 'volume' in self.price_data.columns:
            self.volume_data = self.price_data['volume'].tolist()
        
    def _is_ready_for_calculation(self) -> bool:
        """
        Check if indicator has enough data for calculation.
        
        Returns:
            True if ready for calculation, False otherwise
        """
        return len(self.price_data) >= self.min_bars
        
    def _log_error(self, message: str) -> None:
        """Log error message."""
        if HAS_QUANTCONNECT:
            try:
                from AlgorithmImports import QCAlgorithm
                QCAlgorithm.Error(f"[{self.name}] {message}")
            except:
                print(f"[{self.name}] ERROR: {message}")
        else:
            print(f"[{self.name}] ERROR: {message}")
            
    def _log_debug(self, message: str) -> None:
        """Log debug message."""
        if HAS_QUANTCONNECT:
            try:
                from AlgorithmImports import QCAlgorithm
                QCAlgorithm.Debug(f"[{self.name}] {message}")
            except:
                print(f"[{self.name}] DEBUG: {message}")
        else:
            print(f"[{self.name}] DEBUG: {message}")
            
    def _track_performance(self, start_time: datetime) -> None:
        """Track calculation performance."""
        duration = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(duration)
        
        # Keep only last 100 measurements
        if len(self.calculation_times) > 100:
            self.calculation_times = self.calculation_times[-100:]
            
    def get_average_calculation_time(self) -> float:
        """Get average calculation time in seconds."""
        if not self.calculation_times:
            return 0.0
        return float(np.mean(self.calculation_times))
        
    def reset(self) -> None:
        """Reset indicator state."""
        self.price_data = pd.DataFrame()
        self.volume_data = []
        self.indicator_data = {}
        self.last_update_time = None
        self.update_count = 0
        self.Value = 0.0
        self.IsReady = False
        self.Samples = 0
        
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of current data state."""
        return {
            'name': self.name,
            'timeframe': self.timeframe,
            'bars_count': len(self.price_data),
            'is_ready': self.IsReady,
            'last_update': self.last_update_time,
            'update_count': self.update_count,
            'avg_calculation_time': self.get_average_calculation_time(),
            'current_value': self.Value
        }
        
    def export_data(self, filename: str) -> bool:
        """
        Export indicator data to file.
        
        Args:
            filename: Output filename
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            if filename.endswith('.csv'):
                self.price_data.to_csv(filename, index=False)
            elif filename.endswith('.json'):
                export_data = {
                    'metadata': self.get_data_summary(),
                    'price_data': self.price_data.to_dict('records'),
                    'indicator_data': self.indicator_data
                }
                import json
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            else:
                return False
                
            return True
        except Exception as e:
            self._log_error(f"Error exporting data: {e}")
            return False


class FVGIndicator(FVGBaseIndicator):
    """
    Specialized base class for FVG detection indicators.
    
    This class extends FVGBaseIndicator with FVG-specific functionality
    for detecting and analyzing Fair Value Gaps.
    """
    
    def __init__(self, name: str, timeframe: int = 1, min_fvg_size: float = 0.25):
        """
        Initialize FVG indicator.
        
        Args:
            name: Indicator name
            timeframe: Timeframe in minutes
            min_fvg_size: Minimum FVG size to consider
        """
        super().__init__(name, timeframe)
        
        self.indicator_type = "FVG_DETECTOR"
        self.min_fvg_size = min_fvg_size
        
        # FVG-specific storage
        self.detected_fvgs: List[Dict[str, Any]] = []
        self.fvg_statistics: Dict[str, Any] = {
            'total_detected': 0,
            'bullish_count': 0,
            'bearish_count': 0,
            'average_size': 0.0,
            'last_detection_time': None
        }
        
    def _detect_fvg_pattern(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect FVG patterns in price data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            List of detected FVGs
        """
        fvgs = []
        
        if len(df) < 3:
            return fvgs
            
        for i in range(len(df) - 2):
            candle1 = df.iloc[i]
            candle2 = df.iloc[i + 1]
            candle3 = df.iloc[i + 2]
            
            # Bullish FVG: High[i-2] < Low[i]
            if candle1['high'] < candle3['low']:
                fvg_size = float(candle3['low'] - candle1['high'])
                if fvg_size >= self.min_fvg_size:
                    fvg = {
                        'type': 'bullish',
                        'time': candle2['time'],
                        'top': float(candle1['high']),
                        'bottom': float(candle3['low']),
                        'size': fvg_size,
                        'timeframe': self.timeframe,
                        'volume': float(candle2['volume']),
                        'strength': self._calculate_fvg_strength(candle1, candle2, candle3)
                    }
                    fvgs.append(fvg)
                    
            # Bearish FVG: Low[i-2] > High[i]
            elif candle1['low'] > candle3['high']:
                fvg_size = float(candle1['low'] - candle3['high'])
                if fvg_size >= self.min_fvg_size:
                    fvg = {
                        'type': 'bearish',
                        'time': candle2['time'],
                        'top': float(candle3['high']),
                        'bottom': float(candle1['low']),
                        'size': fvg_size,
                        'timeframe': self.timeframe,
                        'volume': float(candle2['volume']),
                        'strength': self._calculate_fvg_strength(candle1, candle2, candle3)
                    }
                    fvgs.append(fvg)
                    
        return fvgs
        
    def _calculate_fvg_strength(self, candle1: pd.Series, candle2: pd.Series, candle3: pd.Series) -> float:
        """
        Calculate strength of an FVG based on candle characteristics.
        
        Args:
            candle1, candle2, candle3: Three candles in the FVG pattern
            
        Returns:
            Strength score between 0 and 1
        """
        # Base strength from FVG size relative to candle ranges
        avg_range = float((candle1['high'] - candle1['low'] + 
                          candle2['high'] - candle2['low'] + 
                          candle3['high'] - candle3['low']) / 3)
        
        if avg_range == 0.0:
            return 0.0
            
        # Volume contribution
        volume_factor = min(float(candle2['volume']) / 1000000, 1.0)
        
        # Price movement contribution
        price_move = abs(float(candle3['close'] - candle1['open'])) / avg_range
        price_factor = min(price_move / 2.0, 1.0)
        
        # Combined strength
        strength = (volume_factor + price_factor) / 2.0
        return min(strength, 1.0)
        
    def _update_fvg_statistics(self, new_fvgs: List[Dict[str, Any]]) -> None:
        """Update FVG detection statistics."""
        if not new_fvgs:
            return
            
        self.fvg_statistics['total_detected'] += len(new_fvgs)
        self.fvg_statistics['bullish_count'] += len([f for f in new_fvgs if f['type'] == 'bullish'])
        self.fvg_statistics['bearish_count'] += len([f for f in new_fvgs if f['type'] == 'bearish'])
        
        if new_fvgs:
            sizes = [f['size'] for f in new_fvgs]
            current_avg = float(np.mean(sizes))
            total_count = self.fvg_statistics['total_detected']
            prev_avg = self.fvg_statistics['average_size']
            self.fvg_statistics['average_size'] = ((prev_avg * (total_count - len(new_fvgs)) + current_avg * len(new_fvgs)) / total_count)
            self.fvg_statistics['last_detection_time'] = max(f['time'] for f in new_fvgs)
            
    def get_fvg_statistics(self) -> Dict[str, Any]:
        """Get current FVG detection statistics."""
        return self.fvg_statistics.copy()
        
    def get_recent_fvgs(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get most recent FVG detections."""
        return self.detected_fvgs[-count:] if self.detected_fvgs else []