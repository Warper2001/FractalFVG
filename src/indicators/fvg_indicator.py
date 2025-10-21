"""
Fair Value Gap (FVG) Indicator for Multi-Timeframe Analysis.

This module implements the FVG detection indicator that extends the base indicator
class to provide comprehensive FVG detection across all timeframes (1-60 minutes)
for the FVG Confluence Trading Strategy.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging

from .base_indicator import FVGIndicator
from ..models.fvg import FVG, FVGType, ConfluenceArea, VolumeAnomaly
from ..utils.helpers import calculate_gap_size, validate_fvg_conditions, create_fvg_id

logger = logging.getLogger(__name__)


class FairValueGapIndicator(FVGIndicator):
    """
    Advanced FVG detection indicator for multi-timeframe analysis.
    
    This indicator provides comprehensive Fair Value Gap detection with:
    - Three-candle pattern recognition
    - Multi-timeframe support (1-60 minutes)
    - Volume confirmation
    - Strength scoring
    - Performance optimization with vectorized NumPy operations
    """
    
    def __init__(self, name: str = "FVG_Indicator", timeframe: int = 1, 
                 min_fvg_size: float = 0.25, enable_volume_filter: bool = True,
                 enable_strength_filter: bool = True, min_strength_threshold: float = 0.3):
        """
        Initialize the FVG indicator.
        
        Args:
            name: Indicator name
            timeframe: Timeframe in minutes
            min_fvg_size: Minimum FVG size (MNQ tick size is 0.25)
            enable_volume_filter: Enable volume-based filtering
            enable_strength_filter: Enable strength-based filtering
            min_strength_threshold: Minimum strength threshold for FVGs
        """
        super().__init__(name, timeframe, min_fvg_size)
        
        # Enhanced configuration
        self.enable_volume_filter = enable_volume_filter
        self.enable_strength_filter = enable_strength_filter
        self.min_strength_threshold = min_strength_threshold
        
        # Volume analysis parameters
        self.volume_period = 20
        self.volume_multiplier = 2.0
        
        # Performance tracking
        self.detection_stats = {
            'total_patterns_analyzed': 0,
            'fvgs_detected': 0,
            'fvgs_filtered_by_size': 0,
            'fvgs_filtered_by_strength': 0,
            'fvgs_filtered_by_volume': 0,
            'bullish_fvgs': 0,
            'bearish_fvgs': 0,
            'average_fvg_size': 0.0,
            'last_detection_time': None
        }
        
        logger.info(f"FVG Indicator initialized: {name}, timeframe: {timeframe}min")
        
    def Update(self, input_data: Any) -> bool:
        """
        Update indicator with new data.
        
        Args:
            input_data: New price/volume data
            
        Returns:
            True if indicator updated successfully, False otherwise
        """
        try:
            # Validate input data
            if not self._validate_input_data(input_data):
                return False
                
            # Extract price data
            price_data = self._extract_price_data(input_data)
            if price_data is None:
                return False
                
            # Add price bar to storage
            self._add_price_bar(price_data)
            
            # Update timestamp
            self.last_update_time = price_data.get('time', datetime.now())
            self.update_count += 1
            
            # Check if ready for FVG detection
            if not self._is_ready_for_calculation():
                return False
                
            # Perform FVG detection
            self._detect_and_store_fvgs()
            
            # Update indicator value (number of active FVGs)
            self.Value = len(self.detected_fvgs)
            self.Samples = self.update_count
            self.IsReady = True
            
            return True
            
        except Exception as e:
            self._log_error(f"Error updating indicator: {e}")
            return False
            
    def _detect_and_store_fvgs(self) -> None:
        """Detect FVGs and store valid ones using enhanced three-candle logic."""
        start_time = datetime.now()
        
        # Detect FVG patterns using enhanced three-candle logic
        new_fvgs = self._detect_enhanced_fvg_pattern(self.price_data)
        
        # Update statistics
        self.detection_stats['total_patterns_analyzed'] += len(self.price_data) - 2
        self.detection_stats['fvgs_detected'] += len(new_fvgs)
        
        # Filter FVGs
        filtered_fvgs = self._filter_fvgs(new_fvgs)
        
        # Update filter statistics
        size_filtered = len([f for f in new_fvgs if f['size'] < self.min_fvg_size])
        strength_filtered = len([f for f in new_fvgs if f['strength'] < self.min_strength_threshold])
        volume_filtered = len([f for f in new_fvgs if self._is_volume_insufficient(f)])
        
        self.detection_stats['fvgs_filtered_by_size'] += size_filtered
        self.detection_stats['fvgs_filtered_by_strength'] += strength_filtered
        self.detection_stats['fvgs_filtered_by_volume'] += volume_filtered
        
        # Update type statistics
        self.detection_stats['bullish_fvgs'] += len([f for f in filtered_fvgs if f['type'] == 'bullish'])
        self.detection_stats['bearish_fvgs'] += len([f for f in filtered_fvgs if f['type'] == 'bearish'])
        
        # Update average size
        if filtered_fvgs:
            sizes = [f['size'] for f in filtered_fvgs]
            current_avg = np.mean(sizes)
            total_detected = self.detection_stats['fvgs_detected']
            if total_detected > 0:
                prev_avg = self.detection_stats['average_fvg_size']
                self.detection_stats['average_fvg_size'] = (
                    (prev_avg * (total_detected - len(filtered_fvgs)) + current_avg * len(filtered_fvgs)) / total_detected
                )
                
        # Store filtered FVGs
        self.detected_fvgs = filtered_fvgs
        if filtered_fvgs:
            self.detection_stats['last_detection_time'] = max(f['time'] for f in filtered_fvgs)
            
        # Track performance
        self._track_performance(start_time)
        
        # Log detection
        if len(filtered_fvgs) > 0:
            self._log_debug(f"Detected {len(filtered_fvgs)} FVGs on {self.timeframe}min timeframe")
            
    def _filter_fvgs(self, fvgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply filters to detected FVGs.
        
        Args:
            fvgs: List of detected FVGs
            
        Returns:
            List of filtered FVGs
        """
        filtered_fvgs = []
        
        for fvg in fvgs:
            # Size filter
            if fvg['size'] < self.min_fvg_size:
                continue
                
            # Strength filter
            if self.enable_strength_filter and fvg['strength'] < self.min_strength_threshold:
                continue
                
            # Volume filter
            if self.enable_volume_filter and self._is_volume_insufficient(fvg):
                continue
                
            filtered_fvgs.append(fvg)
            
        return filtered_fvgs
        
    def _is_volume_insufficient(self, fvg: Dict[str, Any]) -> bool:
        """
        Check if FVG has insufficient volume.
        
        Args:
            fvg: FVG to check
            
        Returns:
            True if volume is insufficient
        """
        if not self.enable_volume_filter:
            return False
            
        # Get volume data around FVG time
        fvg_time = fvg['time']
        volume_at_fvg = fvg.get('volume', 0)
        
        # Calculate volume average
        if len(self.volume_data) >= self.volume_period:
            volume_avg = np.mean(self.volume_data[-self.volume_period:])
            volume_ratio = volume_at_fvg / volume_avg if volume_avg > 0 else 0
            
            # Check if volume meets threshold
            return volume_ratio < self.volume_multiplier
            
        return False
        
    def get_active_fvgs(self, max_age_minutes: int = 240) -> List[Dict[str, Any]]:
        """
        Get currently active FVGs.
        
        Args:
            max_age_minutes: Maximum age of FVGs to consider (default 4 hours)
            
        Returns:
            List of active FVGs
        """
        if not self.detected_fvgs:
            return []
            
        current_time = datetime.now()
        active_fvgs = []
        
        for fvg in self.detected_fvgs:
            fvg_time = fvg['time']
            if isinstance(fvg_time, str):
                fvg_time = datetime.fromisoformat(fvg_time.replace('Z', '+00:00'))
                
            age_minutes = (current_time - fvg_time).total_seconds() / 60
            
            if age_minutes <= max_age_minutes:
                active_fvgs.append(fvg)
                
        return active_fvgs
        
    def get_fvg_by_price_level(self, price: float, tolerance: float = 0.5) -> List[Dict[str, Any]]:
        """
        Get FVGs at or near a specific price level.
        
        Args:
            price: Price level to search
            tolerance: Price tolerance for matching
            
        Returns:
            List of FVGs at the price level
        """
        matching_fvgs = []
        
        for fvg in self.detected_fvgs:
            # Check if price is within FVG range
            if (fvg['bottom'] - tolerance) <= price <= (fvg['top'] + tolerance):
                matching_fvgs.append(fvg)
                
        return matching_fvgs
        
    def get_fvg_statistics(self) -> Dict[str, Any]:
        """Get comprehensive FVG detection statistics."""
        stats = self.detection_stats.copy()
        
        # Add current state
        stats.update({
            'current_active_fvgs': len(self.get_active_fvgs()),
            'timeframe': self.timeframe,
            'min_fvg_size': self.min_fvg_size,
            'min_strength_threshold': self.min_strength_threshold,
            'volume_filter_enabled': self.enable_volume_filter,
            'strength_filter_enabled': self.enable_strength_filter,
            'last_update': self.last_update_time,
            'update_count': self.update_count
        })
        
        # Calculate detection rate
        if stats['total_patterns_analyzed'] > 0:
            stats['detection_rate'] = stats['fvgs_detected'] / stats['total_patterns_analyzed']
        else:
            stats['detection_rate'] = 0.0
            
        # Calculate filter efficiency
        if stats['fvgs_detected'] > 0:
            total_filtered = (stats['fvgs_filtered_by_size'] + 
                            stats['fvgs_filtered_by_strength'] + 
                            stats['fvgs_filtered_by_volume'])
            stats['filter_efficiency'] = total_filtered / stats['fvgs_detected']
        else:
            stats['filter_efficiency'] = 0.0
            
        return stats
        
    def export_fvg_data(self, filename: str, include_statistics: bool = True) -> bool:
        """
        Export FVG data to file.
        
        Args:
            filename: Output filename
            include_statistics: Whether to include statistics
            
        Returns:
            True if export successful
        """
        try:
            export_data = {
                'fvgs': self.detected_fvgs,
                'metadata': {
                    'timeframe': self.timeframe,
                    'min_fvg_size': self.min_fvg_size,
                    'export_time': datetime.now(),
                    'total_fvgs': len(self.detected_fvgs)
                }
            }
            
            if include_statistics:
                export_data['statistics'] = self.get_fvg_statistics()
                
            if filename.endswith('.json'):
                import json
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            elif filename.endswith('.csv') and self.detected_fvgs:
                df = pd.DataFrame(self.detected_fvgs)
                df.to_csv(filename, index=False)
            else:
                return False
                
            self._log_debug(f"FVG data exported to {filename}")
            return True
            
        except Exception as e:
            self._log_error(f"Error exporting FVG data: {e}")
            return False
            
    def reset_statistics(self) -> None:
        """Reset detection statistics."""
        self.detection_stats = {
            'total_patterns_analyzed': 0,
            'fvgs_detected': 0,
            'fvgs_filtered_by_size': 0,
            'fvgs_filtered_by_strength': 0,
            'fvgs_filtered_by_volume': 0,
            'bullish_fvgs': 0,
            'bearish_fvgs': 0,
            'average_fvg_size': 0.0,
            'last_detection_time': None
        }
        
        self._log_debug("FVG detection statistics reset")
        
    def get_confluence_candidates(self, other_timeframes: List['FairValueGapIndicator']) -> List[Dict[str, Any]]:
        """
        Get FVGs that are candidates for confluence analysis.
        
        Args:
            other_timeframes: List of FVG indicators from other timeframes
            
        Returns:
            List of confluence candidate FVGs
        """
        candidates = []
        
        for fvg in self.detected_fvgs:
            # Check if this FVG has confluence with other timeframes
            confluence_count = 0
            confluence_timeframes = []
            
            for other_indicator in other_timeframes:
                if other_indicator.timeframe == self.timeframe:
                    continue
                    
                # Look for overlapping FVGs in other timeframe
                other_fvgs = other_indicator.get_fvg_by_price_level(
                    (fvg['top'] + fvg['bottom']) / 2, 
                    tolerance=1.0
                )
                
                if other_fvgs:
                    confluence_count += 1
                    confluence_timeframes.append(other_indicator.timeframe)
                    
            # Add confluence information
            if confluence_count > 0:
                fvg_with_confluence = fvg.copy()
                fvg_with_confluence.update({
                    'confluence_count': confluence_count,
                    'confluence_timeframes': confluence_timeframes,
                    'confluence_score': min(confluence_count * 20, 100)  # Simple scoring
                })
                candidates.append(fvg_with_confluence)
                
        return candidates
        
    def _detect_enhanced_fvg_pattern(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect FVG patterns using enhanced three-candle logic.
        
        This implements the three-candle FVG detection logic:
        - Bullish FVG: High[i-2] < Low[i] (gap between candle i-2 high and candle i low)
        - Bearish FVG: Low[i-2] > High[i] (gap between candle i-2 low and candle i high)
        - Enhanced with strength calculation and volume confirmation
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            List of detected FVGs with enhanced attributes
        """
        fvgs = []
        
        if len(df) < 3:
            return fvgs
            
        # Convert to numpy arrays for vectorized operations
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        volumes = df['volume'].values
        times = df['time'].values
        
        # Vectorized FVG detection
        for i in range(len(df) - 2):
            # Three-candle pattern: candle i-2, candle i-1, candle i
            high_i_minus_2 = highs[i]
            low_i_minus_2 = lows[i]
            high_i = highs[i + 2]
            low_i = lows[i + 2]
            
            # Calculate mid candle characteristics for strength
            mid_high = highs[i + 1]
            mid_low = lows[i + 1]
            mid_close = closes[i + 1]
            mid_volume = volumes[i + 1]
            mid_time = times[i + 1]
            
            # Bullish FVG detection: High[i-2] < Low[i]
            if high_i_minus_2 < low_i:
                fvg_size = float(low_i - high_i_minus_2)
                
                if fvg_size >= self.min_fvg_size:
                    # Enhanced strength calculation using three-candle logic
                    strength = self._calculate_enhanced_fvg_strength(
                        high_i_minus_2, low_i_minus_2, mid_high, mid_low, mid_close, 
                        high_i, low_i, mid_volume, i, df
                    )
                    
                    # Calculate additional metrics
                    price_momentum = self._calculate_price_momentum(df, i)
                    volume_anomaly = self._detect_volume_anomaly(df, i + 1)
                    
                    fvg = {
                        'type': 'bullish',
                        'time': mid_time,
                        'top': float(high_i_minus_2),
                        'bottom': float(low_i),
                        'midpoint': float((high_i_minus_2 + low_i) / 2),
                        'size': fvg_size,
                        'timeframe': self.timeframe,
                        'volume': float(mid_volume),
                        'strength': strength,
                        'price_momentum': price_momentum,
                        'volume_anomaly': volume_anomaly,
                        'candle_indices': [i, i + 1, i + 2],
                        'confidence': self._calculate_fvg_confidence(fvg_size, strength, volume_anomaly)
                    }
                    fvgs.append(fvg)
                    
            # Bearish FVG detection: Low[i-2] > High[i]
            elif low_i_minus_2 > high_i:
                fvg_size = float(low_i_minus_2 - high_i)
                
                if fvg_size >= self.min_fvg_size:
                    # Enhanced strength calculation
                    strength = self._calculate_enhanced_fvg_strength(
                        high_i_minus_2, low_i_minus_2, mid_high, mid_low, mid_close,
                        high_i, low_i, mid_volume, i, df
                    )
                    
                    # Calculate additional metrics
                    price_momentum = self._calculate_price_momentum(df, i)
                    volume_anomaly = self._detect_volume_anomaly(df, i + 1)
                    
                    fvg = {
                        'type': 'bearish',
                        'time': mid_time,
                        'top': float(high_i),
                        'bottom': float(low_i_minus_2),
                        'midpoint': float((high_i + low_i_minus_2) / 2),
                        'size': fvg_size,
                        'timeframe': self.timeframe,
                        'volume': float(mid_volume),
                        'strength': strength,
                        'price_momentum': price_momentum,
                        'volume_anomaly': volume_anomaly,
                        'candle_indices': [i, i + 1, i + 2],
                        'confidence': self._calculate_fvg_confidence(fvg_size, strength, volume_anomaly)
                    }
                    fvgs.append(fvg)
                    
        return fvgs
        
    def _calculate_enhanced_fvg_strength(self, high_i_minus_2: float, low_i_minus_2: float,
                                       mid_high: float, mid_low: float, mid_close: float,
                                       high_i: float, low_i: float, mid_volume: float,
                                       index: int, df: pd.DataFrame) -> float:
        """
        Calculate enhanced FVG strength using three-candle analysis.
        
        Args:
            high_i_minus_2, low_i_minus_2: OHLC of candle i-2
            mid_high, mid_low, mid_close: OHLC of candle i-1 (middle candle)
            high_i, low_i: OHLC of candle i
            mid_volume: Volume of middle candle
            index: Index in DataFrame
            df: DataFrame for context
            
        Returns:
            Strength score between 0 and 1
        """
        # 1. Gap size strength (larger gaps are stronger)
        gap_size = abs(low_i - high_i_minus_2) if high_i_minus_2 < low_i else abs(low_i_minus_2 - high_i)
        avg_range = float(np.mean([high_i_minus_2 - low_i_minus_2, mid_high - mid_low, high_i - low_i]))
        gap_strength = min(float(gap_size / (avg_range * 2)), 1.0) if avg_range > 0 else 0.0
        
        # 2. Middle candle strength (strong continuation signal)
        mid_candle_range = mid_high - mid_low
        mid_body_size = abs(mid_close - ((mid_high + mid_low) / 2))
        mid_strength = min(float(mid_body_size / mid_candle_range), 1.0) if mid_candle_range > 0 else 0.0
        
        # 3. Volume strength (higher volume confirms strength)
        if len(df) > index + 10:  # Ensure we have enough data for volume average
            volume_context = float(df['volume'].iloc[max(0, index-5):index+5].mean())
            volume_strength = min(float(mid_volume / (volume_context * 1.5)), 1.0) if volume_context > 0 else 0.0
        else:
            volume_strength = min(float(mid_volume / 100000), 1.0)  # Fallback for insufficient data
            
        # 4. Price momentum strength
        if index > 0:
            price_change = abs(float(df['close'].iloc[index + 2] - df['close'].iloc[index]))
            price_range = float(df['high'].iloc[index:index+3].max() - df['low'].iloc[index:index+3].min())
            momentum_strength = min(float(price_change / price_range), 1.0) if price_range > 0 else 0.0
        else:
            momentum_strength = 0.0
            
        # 5. Timeframe weighting (higher timeframes get more weight)
        timeframe_weight = min(self.timeframe / 60.0, 1.0)  # Normalize to 0-1
        
        # Combine all strength factors with weights
        combined_strength = float(
            gap_strength * 0.3 +      # 30% weight to gap size
            mid_strength * 0.25 +     # 25% weight to middle candle
            volume_strength * 0.25 +  # 25% weight to volume
            momentum_strength * 0.15 + # 15% weight to momentum
            timeframe_weight * 0.05    # 5% weight to timeframe
        )
        
        return min(combined_strength, 1.0)
        
    def _calculate_price_momentum(self, df: pd.DataFrame, index: int) -> float:
        """
        Calculate price momentum around FVG formation.
        
        Args:
            df: DataFrame with price data
            index: Starting index of FVG pattern
            
        Returns:
            Momentum score between -1 and 1
        """
        if index + 3 >= len(df) or index < 2:
            return 0.0
            
        # Calculate price change before and after FVG
        price_before = df['close'].iloc[index]
        price_after = df['close'].iloc[index + 2]
        
        # Calculate momentum as normalized price change
        price_range = df['high'].iloc[index-2:index+3].max() - df['low'].iloc[index-2:index+3].min()
        
        if price_range > 0:
            momentum = float((price_after - price_before) / price_range)
            return max(min(momentum, 1.0), -1.0)
            
        return 0.0
        
    def _detect_volume_anomaly(self, df: pd.DataFrame, mid_index: int) -> float:
        """
        Detect volume anomalies around FVG formation.
        
        Args:
            df: DataFrame with volume data
            mid_index: Index of middle candle in FVG pattern
            
        Returns:
            Volume anomaly score (1.0 = significant anomaly, 0.0 = normal)
        """
        if mid_index >= len(df):
            return 0.0
            
        mid_volume = df['volume'].iloc[mid_index]
        
        # Calculate volume context (average volume around the FVG)
        start_idx = max(0, mid_index - 10)
        end_idx = min(len(df), mid_index + 10)
        
        if end_idx - start_idx < 5:
            return 0.0
            
        context_volumes = df['volume'].iloc[start_idx:end_idx]
        avg_volume = context_volumes.mean()
        volume_std = context_volumes.std()
        
        if avg_volume > 0 and volume_std > 0:
            # Calculate z-score of volume
            volume_zscore = float(abs(mid_volume - avg_volume) / volume_std)
            # Convert to anomaly score (0-1, where 1 is highly anomalous)
            anomaly_score = min(float(volume_zscore / 3.0), 1.0)  # 3 sigma = maximum anomaly
            return anomaly_score
            
        return 0.0
        
    def _calculate_fvg_confidence(self, size: float, strength: float, volume_anomaly: float) -> float:
        """
        Calculate overall confidence in FVG detection.
        
        Args:
            size: FVG size
            strength: FVG strength score
            volume_anomaly: Volume anomaly score
            
        Returns:
            Confidence score between 0 and 1
        """
        # Size confidence (larger FVGs are more reliable)
        size_confidence = min(size / 2.0, 1.0)  # 2 points = maximum confidence
        
        # Combined confidence with weights
        confidence = float(
            size_confidence * 0.4 +      # 40% weight to size
            strength * 0.4 +              # 40% weight to strength
            volume_anomaly * 0.2          # 20% weight to volume anomaly
        )
        
        return min(confidence, 1.0)