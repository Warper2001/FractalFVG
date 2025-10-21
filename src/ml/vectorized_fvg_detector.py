"""
Vectorized FVG Detector using NumPy for optimized performance across 60 timeframes.
Provides high-performance FVG detection using vectorized operations.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import time

from ..utils.helpers import validate_price_data, validate_volume_data


@dataclass
class VectorizedFVGResult:
    """Result of vectorized FVG detection."""
    fvg_type: np.ndarray  # 'bullish' or 'bearish' for each detection
    top: np.ndarray       # Top price of each FVG
    bottom: np.ndarray    # Bottom price of each FVG
    midpoint: np.ndarray  # Midpoint of each FVG
    size: np.ndarray      # Size of each FVG
    volume: np.ndarray    # Volume at FVG formation
    strength: np.ndarray  # Strength score of each FVG
    confidence: np.ndarray  # Confidence score of each FVG
    indices: np.ndarray   # Candle indices where FVGs were detected
    timestamps: np.ndarray  # Timestamps of FVG detections
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame."""
        return pd.DataFrame({
            'fvg_type': self.fvg_type,
            'top': self.top,
            'bottom': self.bottom,
            'midpoint': self.midpoint,
            'size': self.size,
            'volume': self.volume,
            'strength': self.strength,
            'confidence': self.confidence,
            'candle_index': self.indices,
            'timestamp': self.timestamps
        })
    
    def filter_by_size(self, min_size: float) -> 'VectorizedFVGResult':
        """Filter FVGs by minimum size."""
        mask = self.size >= min_size
        return VectorizedFVGResult(
            fvg_type=self.fvg_type[mask],
            top=self.top[mask],
            bottom=self.bottom[mask],
            midpoint=self.midpoint[mask],
            size=self.size[mask],
            volume=self.volume[mask],
            strength=self.strength[mask],
            confidence=self.confidence[mask],
            indices=self.indices[mask],
            timestamps=self.timestamps[mask]
        )


class VectorizedFVGDetector:
    """
    High-performance FVG detector using vectorized NumPy operations.
    
    Optimized for processing 60 timeframes simultaneously with efficient
    memory usage and parallel computation capabilities.
    """
    
    def __init__(self, min_fvg_size: float = 0.25, 
                 enable_strength_calculation: bool = True,
                 enable_confidence_calculation: bool = True,
                 batch_size: int = 1000):
        """
        Initialize vectorized FVG detector.
        
        Args:
            min_fvg_size: Minimum FVG size to consider
            enable_strength_calculation: Whether to calculate strength scores
            enable_confidence_calculation: Whether to calculate confidence scores
            batch_size: Batch size for processing large datasets
        """
        self.min_fvg_size = min_fvg_size
        self.enable_strength_calculation = enable_strength_calculation
        self.enable_confidence_calculation = enable_confidence_calculation
        self.batch_size = batch_size
        
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.performance_stats = {
            'total_detections': 0,
            'total_processing_time': 0.0,
            'avg_processing_time': 0.0,
            'batches_processed': 0,
            'candles_processed': 0
        }
        
        self.logger.info("Vectorized FVG Detector initialized")
        
    def detect_fvgs_vectorized(self, ohlc_data: np.ndarray, 
                              volume_data: Optional[np.ndarray] = None,
                              timestamps: Optional[np.ndarray] = None) -> VectorizedFVGResult:
        """
        Detect FVGs using vectorized NumPy operations.
        
        Args:
            ohlc_data: OHLC data as numpy array shape (n, 4) - [open, high, low, close]
            volume_data: Volume data as numpy array shape (n,)
            timestamps: Timestamp data as numpy array
            
        Returns:
            VectorizedFVGResult with detected FVGs
        """
        start_time = time.time()
        
        try:
            # Validate input data
            if not self._validate_input_data(ohlc_data, volume_data):
                raise ValueError("Invalid input data")
                
            n_candles = len(ohlc_data)
            if n_candles < 3:
                return VectorizedFVGResult(
                    fvg_type=np.array([]),
                    top=np.array([]),
                    bottom=np.array([]),
                    midpoint=np.array([]),
                    size=np.array([]),
                    volume=np.array([]),
                    strength=np.array([]),
                    confidence=np.array([]),
                    indices=np.array([]),
                    timestamps=np.array([])
                )
                
            # Extract OHLC columns
            opens = ohlc_data[:, 0]
            highs = ohlc_data[:, 1]
            lows = ohlc_data[:, 2]
            closes = ohlc_data[:, 3]
            
            # Vectorized FVG detection
            # Create sliding windows for three-candle patterns
            high_i_minus_2 = highs[:-2]  # High of candle i-2
            low_i_minus_2 = lows[:-2]    # Low of candle i-2
            high_i = highs[2:]           # High of candle i
            low_i = lows[2:]             # Low of candle i
            
            # Bullish FVG detection: High[i-2] < Low[i]
            bullish_mask = high_i_minus_2 < low_i
            bullish_sizes = low_i - high_i_minus_2
            bullish_valid = bullish_mask & (bullish_sizes >= self.min_fvg_size)
            
            # Bearish FVG detection: Low[i-2] > High[i]
            bearish_mask = low_i_minus_2 > high_i
            bearish_sizes = low_i_minus_2 - high_i
            bearish_valid = bearish_mask & (bearish_sizes >= self.min_fvg_size)
            
            # Combine results
            valid_detections = bullish_valid | bearish_valid
            
            if not np.any(valid_detections):
                return VectorizedFVGResult(
                    fvg_type=np.array([]),
                    top=np.array([]),
                    bottom=np.array([]),
                    midpoint=np.array([]),
                    size=np.array([]),
                    volume=np.array([]),
                    strength=np.array([]),
                    confidence=np.array([]),
                    indices=np.array([]),
                    timestamps=np.array([])
                )
                
            # Extract detection indices (add 1 for middle candle)
            detection_indices = np.where(valid_detections)[0] + 1
            
            # Determine FVG types
            fvg_types = np.full(len(detection_indices), 'unknown', dtype=object)
            fvg_types[bullish_valid[valid_detections]] = 'bullish'
            fvg_types[bearish_valid[valid_detections]] = 'bearish'
            
            # Calculate FVG properties
            tops = np.where(bullish_valid[valid_detections], 
                          high_i_minus_2[valid_detections], 
                          high_i[valid_detections])
            bottoms = np.where(bullish_valid[valid_detections], 
                             low_i[valid_detections], 
                             low_i_minus_2[valid_detections])
            sizes = np.abs(tops - bottoms)
            midpoints = (tops + bottoms) / 2
            
            # Get volume data (middle candle volume)
            if volume_data is not None and len(volume_data) > 0:
                middle_volumes = volume_data[1:-1][valid_detections]
            else:
                middle_volumes = np.zeros(len(detection_indices))
                
            # Calculate strength scores if enabled
            if self.enable_strength_calculation:
                strengths = self._calculate_strength_vectorized(
                    ohlc_data, valid_detections, middle_volumes
                )
            else:
                strengths = np.ones(len(detection_indices))
                
            # Calculate confidence scores if enabled
            if self.enable_confidence_calculation:
                confidences = self._calculate_confidence_vectorized(
                    sizes, strengths, middle_volumes
                )
            else:
                confidences = np.ones(len(detection_indices))
                
            # Get timestamps
            if timestamps is not None and len(timestamps) > 0:
                detection_timestamps = timestamps[1:-1][valid_detections]
            else:
                detection_timestamps = np.full(len(detection_indices), datetime.now(), dtype=object)
                
            # Create result
            result = VectorizedFVGResult(
                fvg_type=fvg_types,
                top=tops,
                bottom=bottoms,
                midpoint=midpoints,
                size=sizes,
                volume=middle_volumes,
                strength=strengths,
                confidence=confidences,
                indices=detection_indices,
                timestamps=detection_timestamps
            )
            
            # Update performance stats
            processing_time = time.time() - start_time
            self._update_performance_stats(len(detection_indices), processing_time, n_candles)
            
            self.logger.debug(f"Vectorized detection completed: {len(detection_indices)} FVGs in {processing_time:.4f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in vectorized FVG detection: {e}")
            raise
            
    def _validate_input_data(self, ohlc_data: np.ndarray, 
                           volume_data: Optional[np.ndarray] = None) -> bool:
        """Validate input data for vectorized processing."""
        try:
            # Check OHLC data
            if ohlc_data is None or len(ohlc_data) == 0:
                return False
                
            if ohlc_data.ndim != 2 or ohlc_data.shape[1] != 4:
                return False
                
            # Check for invalid values
            if np.any(np.isnan(ohlc_data)) or np.any(np.isinf(ohlc_data)):
                return False
                
            if np.any(ohlc_data <= 0):
                return False
                
            # Check volume data if provided
            if volume_data is not None:
                if len(volume_data) != len(ohlc_data):
                    return False
                    
                if np.any(np.isnan(volume_data)) or np.any(np.isinf(volume_data)):
                    return False
                    
                if np.any(volume_data < 0):
                    return False
                    
            return True
            
        except Exception:
            return False
            
    def _calculate_strength_vectorized(self, ohlc_data: np.ndarray, 
                                     valid_detections: np.ndarray,
                                     volumes: np.ndarray) -> np.ndarray:
        """
        Calculate strength scores using vectorized operations.
        
        Args:
            ohlc_data: OHLC data
            valid_detections: Boolean mask for valid detections
            volumes: Volume data for middle candles
            
        Returns:
            Strength scores array
        """
        try:
            # Extract OHLC for the three-candle patterns
            n_patterns = len(ohlc_data) - 2
            
            # Get ranges for each candle in the patterns
            ranges_1 = ohlc_data[:-2, 1] - ohlc_data[:-2, 2]  # High - Low for candle i-2
            ranges_2 = ohlc_data[1:-1, 1] - ohlc_data[1:-1, 2]  # High - Low for candle i-1
            ranges_3 = ohlc_data[2:, 1] - ohlc_data[2:, 2]  # High - Low for candle i
            
            # Average range for each pattern
            avg_ranges = (ranges_1 + ranges_2 + ranges_3) / 3
            
            # Gap size strength
            high_i_minus_2 = ohlc_data[:-2, 1]
            low_i_minus_2 = ohlc_data[:-2, 2]
            high_i = ohlc_data[2:, 1]
            low_i = ohlc_data[2:, 2]
            
            gap_sizes = np.where(
                high_i_minus_2 < low_i,
                low_i - high_i_minus_2,
                np.where(low_i_minus_2 > high_i, low_i_minus_2 - high_i, 0)
            )
            
            gap_strength = np.zeros_like(gap_sizes)
            valid_avg_ranges = avg_ranges > 0
            gap_strength[valid_avg_ranges] = np.minimum(
                gap_sizes[valid_avg_ranges] / (avg_ranges[valid_avg_ranges] * 2), 1.0
            )
            
            # Volume strength (normalized)
            max_volume = np.max(volumes) if len(volumes) > 0 and np.max(volumes) > 0 else 1
            volume_strength = np.minimum(volumes / (max_volume * 0.5), 1.0)
            
            # Price momentum strength
            price_changes = np.abs(ohlc_data[2:, 3] - ohlc_data[:-2, 0])  # |close[i] - open[i-2]|
            momentum_strength = np.zeros_like(price_changes)
            momentum_strength[valid_avg_ranges] = np.minimum(
                price_changes[valid_avg_ranges] / avg_ranges[valid_avg_ranges], 1.0
            )
            
            # Combined strength (weighted average)
            combined_strength = (
                gap_strength * 0.4 +      # 40% weight to gap size
                volume_strength * 0.3 +    # 30% weight to volume
                momentum_strength * 0.3    # 30% weight to momentum
            )
            
            # Return strength for valid detections only
            return combined_strength[valid_detections]
            
        except Exception as e:
            self.logger.error(f"Error calculating strength: {e}")
            return np.ones(np.sum(valid_detections))
            
    def _calculate_confidence_vectorized(self, sizes: np.ndarray, 
                                       strengths: np.ndarray,
                                       volumes: np.ndarray) -> np.ndarray:
        """
        Calculate confidence scores using vectorized operations.
        
        Args:
            sizes: FVG sizes
            strengths: Strength scores
            volumes: Volume data
            
        Returns:
            Confidence scores array
        """
        try:
            # Size confidence (larger FVGs are more reliable)
            max_size = np.max(sizes) if len(sizes) > 0 and np.max(sizes) > 0 else 1
            size_confidence = np.minimum(sizes / (max_size * 0.8), 1.0)
            
            # Strength confidence
            strength_confidence = strengths
            
            # Volume confidence (normalized)
            max_volume = np.max(volumes) if len(volumes) > 0 and np.max(volumes) > 0 else 1
            volume_confidence = np.minimum(volumes / (max_volume * 0.3), 1.0)
            
            # Combined confidence
            combined_confidence = (
                size_confidence * 0.4 +      # 40% weight to size
                strength_confidence * 0.4 +  # 40% weight to strength
                volume_confidence * 0.2       # 20% weight to volume
            )
            
            return np.minimum(combined_confidence, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {e}")
            return np.ones(len(sizes))
            
    def detect_multiple_timeframes(self, timeframe_data: Dict[int, np.ndarray],
                                 timeframe_volumes: Optional[Dict[int, np.ndarray]] = None,
                                 timeframe_timestamps: Optional[Dict[int, np.ndarray]] = None) -> Dict[int, VectorizedFVGResult]:
        """
        Detect FVGs across multiple timeframes simultaneously.
        
        Args:
            timeframe_data: Dictionary of timeframe -> OHLC data
            timeframe_volumes: Dictionary of timeframe -> volume data
            timeframe_timestamps: Dictionary of timeframe -> timestamp data
            
        Returns:
            Dictionary of timeframe -> VectorizedFVGResult
        """
        results = {}
        
        for timeframe, ohlc_data in timeframe_data.items():
            try:
                volume_data = timeframe_volumes.get(timeframe) if timeframe_volumes else None
                timestamps = timeframe_timestamps.get(timeframe) if timeframe_timestamps else None
                
                result = self.detect_fvgs_vectorized(ohlc_data, volume_data, timestamps)
                results[timeframe] = result
                
                self.logger.debug(f"Timeframe {timeframe}min: {len(result.fvg_type)} FVGs detected")
                
            except Exception as e:
                self.logger.error(f"Error processing timeframe {timeframe}: {e}")
                # Create empty result for failed timeframe
                results[timeframe] = VectorizedFVGResult(
                    fvg_type=np.array([]),
                    top=np.array([]),
                    bottom=np.array([]),
                    midpoint=np.array([]),
                    size=np.array([]),
                    volume=np.array([]),
                    strength=np.array([]),
                    confidence=np.array([]),
                    indices=np.array([]),
                    timestamps=np.array([])
                )
                
        return results
        
    def process_large_dataset(self, ohlc_data: np.ndarray,
                            volume_data: Optional[np.ndarray] = None,
                            timestamps: Optional[np.ndarray] = None) -> VectorizedFVGResult:
        """
        Process large datasets in batches for memory efficiency.
        
        Args:
            ohlc_data: Large OHLC dataset
            volume_data: Volume data
            timestamps: Timestamp data
            
        Returns:
            Combined VectorizedFVGResult
        """
        if len(ohlc_data) <= self.batch_size:
            return self.detect_fvgs_vectorized(ohlc_data, volume_data, timestamps)
            
        all_results = []
        
        for i in range(0, len(ohlc_data) - 2, self.batch_size):
            end_idx = min(i + self.batch_size + 2, len(ohlc_data))
            
            batch_ohlc = ohlc_data[i:end_idx]
            batch_volume = volume_data[i:end_idx] if volume_data is not None else None
            batch_timestamps = timestamps[i:end_idx] if timestamps is not None else None
            
            batch_result = self.detect_fvgs_vectorized(batch_ohlc, batch_volume, batch_timestamps)
            
            if len(batch_result.fvg_type) > 0:
                # Adjust indices to account for batch offset
                batch_result.indices = batch_result.indices + i
                all_results.append(batch_result)
                
        # Combine all batch results
        if not all_results:
            return VectorizedFVGResult(
                fvg_type=np.array([]),
                top=np.array([]),
                bottom=np.array([]),
                midpoint=np.array([]),
                size=np.array([]),
                volume=np.array([]),
                strength=np.array([]),
                confidence=np.array([]),
                indices=np.array([]),
                timestamps=np.array([])
            )
            
        # Concatenate all results
        combined_result = VectorizedFVGResult(
            fvg_type=np.concatenate([r.fvg_type for r in all_results]),
            top=np.concatenate([r.top for r in all_results]),
            bottom=np.concatenate([r.bottom for r in all_results]),
            midpoint=np.concatenate([r.midpoint for r in all_results]),
            size=np.concatenate([r.size for r in all_results]),
            volume=np.concatenate([r.volume for r in all_results]),
            strength=np.concatenate([r.strength for r in all_results]),
            confidence=np.concatenate([r.confidence for r in all_results]),
            indices=np.concatenate([r.indices for r in all_results]),
            timestamps=np.concatenate([r.timestamps for r in all_results])
        )
        
        return combined_result
        
    def _update_performance_stats(self, detection_count: int, 
                                processing_time: float, 
                                candle_count: int) -> None:
        """Update performance statistics."""
        self.performance_stats['total_detections'] += detection_count
        self.performance_stats['total_processing_time'] += processing_time
        self.performance_stats['batches_processed'] += 1
        self.performance_stats['candles_processed'] += candle_count
        
        total_batches = self.performance_stats['batches_processed']
        self.performance_stats['avg_processing_time'] = (
            self.performance_stats['total_processing_time'] / total_batches
        )
        
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = self.performance_stats.copy()
        
        # Calculate additional metrics
        if stats['candles_processed'] > 0:
            stats['detections_per_candle'] = stats['total_detections'] / stats['candles_processed']
            
        if stats['total_processing_time'] > 0:
            stats['detections_per_second'] = stats['total_detections'] / stats['total_processing_time']
            stats['candles_per_second'] = stats['candles_processed'] / stats['total_processing_time']
            
        return stats
        
    def reset_performance_stats(self) -> None:
        """Reset performance statistics."""
        self.performance_stats = {
            'total_detections': 0,
            'total_processing_time': 0.0,
            'avg_processing_time': 0.0,
            'batches_processed': 0,
            'candles_processed': 0
        }