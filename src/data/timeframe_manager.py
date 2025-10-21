"""
TimeframeManager for multi-timeframe consolidator management.
Handles 1-60 minute timeframe consolidators with proper data alignment.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from collections import defaultdict
import logging

# Handle QuantConnect imports
try:
    from QuantConnect.Data.Consolidators import TradeBarConsolidator
    from QuantConnect.Data import TradeBar
    from QuantConnect import Resolution
    QC_AVAILABLE = True
except ImportError:
    QC_AVAILABLE = False
    TradeBar = None  # type: ignore
    TradeBarConsolidator = None  # type: ignore
    logging.warning("QuantConnect not available - using mock consolidators")

from ..utils.config import TimeframeConfig
from ..utils.helpers import validate_timeframe, align_data_to_timeframe


class TimeframeManager:
    """
    Manages multiple timeframe consolidators for FVG detection.
    Supports 1-60 minute timeframes with efficient data handling.
    """
    
    def __init__(self, symbol: str, config: Optional[TimeframeConfig] = None):
        """
        Initialize TimeframeManager.
        
        Args:
            symbol: Trading symbol
            config: Timeframe configuration (optional)
        """
        self.symbol = symbol
        self.config = config or TimeframeConfig()
        self.logger = logging.getLogger(__name__)
        
        # Storage for consolidators and data
        self.consolidators: Dict[int, Any] = {}
        self.data_buffers: Dict[int, List[Any]] = defaultdict(list)
        self.last_update: Dict[int, datetime] = {}
        
        # Initialize consolidators for all timeframes
        self._initialize_consolidators()
        
    def _initialize_consolidators(self) -> None:
        """Initialize consolidators for all configured timeframes (1-60 minutes)."""
        if not QC_AVAILABLE:
            self.logger.info("Using mock consolidators for development")
            # Initialize mock data structures for all timeframes
            for timeframe in self.config.timeframes:
                self.data_buffers[timeframe] = []
                # Don't set last_update to None to avoid type error
            return
            
        successful_initializations = 0
        
        for timeframe in self.config.timeframes:
            try:
                # Create consolidator for each timeframe
                if TradeBarConsolidator is not None:
                    consolidator = TradeBarConsolidator(timedelta(minutes=timeframe))
                    consolidator.DataConsolidated += self._on_data_consolidated
                    
                    self.consolidators[timeframe] = consolidator
                    successful_initializations += 1
                    
                    self.logger.debug(f"Initialized consolidator for {timeframe} minute timeframe")
                else:
                    self.logger.warning(f"TradeBarConsolidator not available for {timeframe}min")
                    
            except Exception as e:
                self.logger.error(f"Failed to initialize consolidator for {timeframe}min: {e}")
                
        self.logger.info(f"Successfully initialized {successful_initializations}/{len(self.config.timeframes)} timeframe consolidators")
        
    def setup_timeframe_alignment(self) -> Dict[int, Dict[str, Any]]:
        """
        Set up proper data alignment across all 1-60 minute timeframes.
        
        Returns:
            Dictionary with alignment configuration for each timeframe
        """
        alignment_config = {}
        
        for timeframe in self.config.timeframes:
            # Calculate alignment parameters based on timeframe
            base_minutes = 1  # Base timeframe
            
            # Determine how many base periods fit into this timeframe
            periods_per_timeframe = timeframe // base_minutes
            
            # Calculate data alignment offset for proper synchronization
            alignment_offset = (timeframe - 1) % base_minutes
            
            # Set buffer sizes based on timeframe importance
            buffer_multiplier = min(timeframe / 15.0, 4.0)  # Higher timeframes get larger buffers
            buffer_size = int(self.config.max_lookback_periods * buffer_multiplier)
            
            alignment_config[timeframe] = {
                'periods_per_timeframe': periods_per_timeframe,
                'alignment_offset': alignment_offset,
                'buffer_size': buffer_size,
                'update_frequency': max(1, timeframe // 5),  # Less frequent updates for higher timeframes
                'data_retention_minutes': timeframe * 100,  # Keep more data for higher timeframes
                'priority': 'high' if timeframe <= 5 else 'medium' if timeframe <= 15 else 'low'
            }
            
        self.logger.info(f"Set up alignment configuration for {len(alignment_config)} timeframes")
        return alignment_config
        
    def validate_timeframe_coverage(self) -> Dict[str, Any]:
        """
        Validate that all 1-60 minute timeframes are properly configured.
        
        Returns:
            Validation report with coverage statistics
        """
        expected_timeframes = set(range(1, 61))
        configured_timeframes = set(self.config.timeframes)
        active_consolidators = set(self.consolidators.keys())
        
        missing_timeframes = expected_timeframes - configured_timeframes
        inactive_timeframes = configured_timeframes - active_consolidators if QC_AVAILABLE else set()
        
        # Calculate coverage statistics
        total_expected = len(expected_timeframes)
        configured_count = len(configured_timeframes)
        active_count = len(active_consolidators)
        
        coverage_percentage = (configured_count / total_expected) * 100
        active_percentage = (active_count / total_expected) * 100 if QC_AVAILABLE else coverage_percentage
        
        validation_report = {
            'total_timeframes_expected': total_expected,
            'timeframes_configured': configured_count,
            'timeframes_active': active_count,
            'coverage_percentage': coverage_percentage,
            'active_percentage': active_percentage,
            'missing_timeframes': sorted(list(missing_timeframes)),
            'inactive_timeframes': sorted(list(inactive_timeframes)) if QC_AVAILABLE else [],
            'is_fully_covered': len(missing_timeframes) == 0,
            'is_fully_active': len(inactive_timeframes) == 0 if QC_AVAILABLE else True,
            'data_buffer_status': self._get_buffer_status(),
            'alignment_status': self._get_alignment_status()
        }
        
        self.logger.info(f"Timeframe coverage validation: {coverage_percentage:.1f}% configured, {active_percentage:.1f}% active")
        
        return validation_report
        
    def _get_buffer_status(self) -> Dict[str, Any]:
        """Get status of data buffers across all timeframes."""
        buffer_status = {
            'total_buffers': len(self.data_buffers),
            'populated_buffers': len([tf for tf, buffer in self.data_buffers.items() if buffer]),
            'empty_buffers': len([tf for tf, buffer in self.data_buffers.items() if not buffer]),
            'average_buffer_size': np.mean([len(buffer) for buffer in self.data_buffers.values()]) if self.data_buffers else 0,
            'max_buffer_size': max([len(buffer) for buffer in self.data_buffers.values()]) if self.data_buffers else 0,
            'min_buffer_size': min([len(buffer) for buffer in self.data_buffers.values()]) if self.data_buffers else 0
        }
        
        return buffer_status
        
    def _get_alignment_status(self) -> Dict[str, Any]:
        """Get alignment status across timeframes."""
        alignment_status = {
            'timeframes_with_recent_data': 0,
            'timeframes_stale': 0,
            'alignment_quality': 'good'
        }
        
        current_time = datetime.now()
        stale_threshold_minutes = 60  # Consider data stale after 1 hour
        
        for timeframe, last_update in self.last_update.items():
            if last_update:
                age_minutes = (current_time - last_update).total_seconds() / 60
                if age_minutes <= stale_threshold_minutes:
                    alignment_status['timeframes_with_recent_data'] += 1
                else:
                    alignment_status['timeframes_stale'] += 1
            else:
                alignment_status['timeframes_stale'] += 1
                
        # Determine alignment quality
        total_timeframes = len(self.config.timeframes)
        if total_timeframes > 0:
            recent_percentage = (alignment_status['timeframes_with_recent_data'] / total_timeframes) * 100
            if recent_percentage >= 80:
                alignment_status['alignment_quality'] = 'excellent'
            elif recent_percentage >= 60:
                alignment_status['alignment_quality'] = 'good'
            elif recent_percentage >= 40:
                alignment_status['alignment_quality'] = 'fair'
            else:
                alignment_status['alignment_quality'] = 'poor'
                
        return alignment_status
                
    def _on_data_consolidated(self, sender: Any, consolidated: Any) -> None:
        """
        Handle consolidated data from consolidators.
        
        Args:
            sender: The consolidator that sent the data
            consolidated: The consolidated trade bar
        """
        if not QC_AVAILABLE:
            return
            
        # Extract timeframe from consolidator
        timeframe = None
        for tf, consolidator in self.consolidators.items():
            if consolidator == sender:
                timeframe = tf
                break
                
        if timeframe is None:
            self.logger.warning("Received data from unknown consolidator")
            return
            
        # Store consolidated data
        self.data_buffers[timeframe].append(consolidated)
        self.last_update[timeframe] = consolidated.EndTime
        
        # Maintain buffer size
        max_buffer = self.config.max_lookback_periods * 2
        if len(self.data_buffers[timeframe]) > max_buffer:
            self.data_buffers[timeframe] = self.data_buffers[timeframe][-max_buffer:]
            
    def add_data(self, data: Any, timeframe: int) -> None:
        """
        Add data to a specific timeframe.
        
        Args:
            data: Trade bar data
            timeframe: Timeframe in minutes
        """
        if not validate_timeframe(timeframe):
            raise ValueError(f"Invalid timeframe: {timeframe}")
            
        if timeframe not in self.config.timeframes:
            self.logger.warning(f"Timeframe {timeframe} not in configured timeframes")
            return
            
        if QC_AVAILABLE and timeframe in self.consolidators and self.consolidators[timeframe] is not None:
            # Use QuantConnect consolidator
            self.consolidators[timeframe].Update(data)
        else:
            # Direct data addition for development
            self._add_direct_data(data, timeframe)
            
    def _add_direct_data(self, data: Any, timeframe: int) -> None:
        """
        Add data directly without consolidator (for development).
        
        Args:
            data: Trade bar data
            timeframe: Timeframe in minutes
        """
        # Create mock TradeBar if needed
        if not hasattr(data, 'Open'):
            # Assume data is a dict or has attributes
            mock_bar = type('MockTradeBar', (), {
                'Open': getattr(data, 'open', data.get('open', 0)),
                'High': getattr(data, 'high', data.get('high', 0)),
                'Low': getattr(data, 'low', data.get('low', 0)),
                'Close': getattr(data, 'close', data.get('close', 0)),
                'Volume': getattr(data, 'volume', data.get('volume', 0)),
                'EndTime': getattr(data, 'endtime', data.get('endtime', datetime.now())),
                'Time': getattr(data, 'time', data.get('time', datetime.now()))
            })()
            data = mock_bar
            
        self.data_buffers[timeframe].append(data)
        self.last_update[timeframe] = data.EndTime
        
        # Maintain buffer size
        max_buffer = self.config.max_lookback_periods * 2
        if len(self.data_buffers[timeframe]) > max_buffer:
            self.data_buffers[timeframe] = self.data_buffers[timeframe][-max_buffer:]
            
    def get_latest_data(self, timeframe: int, periods: Optional[int] = None) -> List[Any]:
        """
        Get latest data for a specific timeframe.
        
        Args:
            timeframe: Timeframe in minutes
            periods: Number of periods to retrieve (default from config)
            
        Returns:
            List of trade bars
        """
        if not validate_timeframe(timeframe):
            raise ValueError(f"Invalid timeframe: {timeframe}")
            
        periods = periods or self.config.max_lookback_periods
        buffer = self.data_buffers.get(timeframe, [])
        
        return buffer[-periods:] if buffer else []
        
    def get_aligned_data(self, target_timeframe: int, 
                        source_timeframes: Optional[List[int]] = None) -> Dict[int, List[Any]]:
        """
        Get aligned data across multiple timeframes.
        
        Args:
            target_timeframe: Target timeframe for alignment
            source_timeframes: Source timeframes to align (default all)
            
        Returns:
            Dictionary of aligned data by timeframe
        """
        source_timeframes = source_timeframes or self.config.timeframes
        aligned_data = {}
        
        for tf in source_timeframes:
            data = self.get_latest_data(tf)
            if data:
                aligned_data[tf] = align_data_to_timeframe(data, target_timeframe)
                
        return aligned_data
        
    def get_latest_prices(self, timeframe: int) -> Optional[Tuple[float, float, float, float]]:
        """
        Get latest OHLC prices for a timeframe.
        
        Args:
            timeframe: Timeframe in minutes
            
        Returns:
            Tuple of (open, high, low, close) or None if no data
        """
        data = self.get_latest_data(timeframe, 1)
        if not data:
            return None
            
        latest = data[-1]
        return (latest.Open, latest.High, latest.Low, latest.Close)
        
    def get_volume_profile(self, timeframe: int, periods: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate volume profile for a timeframe.
        
        Args:
            timeframe: Timeframe in minutes
            periods: Number of periods to analyze
            
        Returns:
            Volume profile statistics
        """
        data = self.get_latest_data(timeframe, periods)
        if not data:
            return {}
            
        volumes = [bar.Volume for bar in data]
        highs = [bar.High for bar in data]
        lows = [bar.Low for bar in data]
        
        return {
            'total_volume': sum(volumes),
            'avg_volume': np.mean(volumes),
            'volume_std': np.std(volumes),
            'max_volume': max(volumes),
            'min_volume': min(volumes),
            'price_range': max(highs) - min(lows),
            'vwap': self._calculate_vwap(data)
        }
        
    def _calculate_vwap(self, data: List[Any]) -> float:
        """Calculate Volume Weighted Average Price."""
        if not data:
            return 0.0
            
        total_pv = sum(bar.Close * bar.Volume for bar in data)
        total_volume = sum(bar.Volume for bar in data)
        
        return total_pv / total_volume if total_volume > 0 else 0.0
        
    def is_data_ready(self, timeframe: int, min_periods: Optional[int] = None) -> bool:
        """
        Check if sufficient data is available for a timeframe.
        
        Args:
            timeframe: Timeframe in minutes
            min_periods: Minimum required periods
            
        Returns:
            True if data is ready
        """
        min_periods = min_periods or self.config.min_periods_required
        return len(self.data_buffers.get(timeframe, [])) >= min_periods
        
    def get_timeframe_status(self) -> Dict[int, Dict[str, Any]]:
        """
        Get status of all timeframes.
        
        Returns:
            Status dictionary by timeframe
        """
        status = {}
        
        for timeframe in self.config.timeframes:
            buffer = self.data_buffers.get(timeframe, [])
            last_update = self.last_update.get(timeframe)
            
            status[timeframe] = {
                'data_count': len(buffer),
                'last_update': last_update,
                'is_ready': self.is_data_ready(timeframe),
                'has_consolidator': timeframe in self.consolidators
            }
            
        return status
        
    def cleanup(self) -> None:
        """Clean up resources and consolidators."""
        if QC_AVAILABLE:
            for consolidator in self.consolidators.values():
                try:
                    consolidator.RemoveConsolidator()
                except:
                    pass
                    
        self.consolidators.clear()
        self.data_buffers.clear()
        self.last_update.clear()
        
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.cleanup()
        except:
            pass