"""
Core FVG (Fair Value Gap) detection algorithms for 1-60 minute timeframes.

This module implements the core detection logic for identifying Fair Value Gaps
across multiple timeframes, with advanced filtering and confluence analysis
capabilities for the FVG Confluence Trading Strategy.
"""

from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass

from ..models.fvg import FVG, FVGType, ConfluenceArea, VolumeAnomaly, FVGList, TimeframeData


@dataclass
class FVGDetectorConfig:
    """Configuration for FVG detection algorithms."""
    min_fvg_size: float = 0.25  # Minimum FVG size (MNQ tick size)
    max_fvg_age_minutes: int = 240  # Maximum age for FVG consideration
    min_strength_threshold: float = 0.3  # Minimum strength threshold
    volume_period: int = 20  # Period for volume moving average
    volume_multiplier: float = 2.0  # Volume anomaly threshold
    confluence_threshold: int = 3  # Minimum timeframes for confluence
    price_tolerance: float = 0.25  # Price tolerance for overlap detection
    time_tolerance_minutes: int = 5  # Time tolerance for confluence
    enable_volume_filter: bool = True
    enable_strength_filter: bool = True
    enable_age_filter: bool = True


class FVGDetector:
    """
    Core FVG detection engine for multi-timeframe analysis.
    
    This class provides comprehensive FVG detection capabilities across all
    timeframes from 1-60 minutes, with advanced filtering and confluence analysis.
    """
    
    def __init__(self, config: Optional[FVGDetectorConfig] = None):
        """
        Initialize the FVG detector.
        
        Args:
            config: Configuration for detection parameters
        """
        self.config = config or FVGDetectorConfig()
        self.timeframes = list(range(1, 61))  # 1-60 minute timeframes
        self.detected_fvgs: Dict[int, FVGList] = {}
        self.confluence_areas: List[ConfluenceArea] = []
        
    def detect_fvgs_timeframe(self, df: pd.DataFrame, timeframe: int) -> FVGList:
        """
        Detect FVGs for a specific timeframe.
        
        Args:
            df: OHLCV data for the timeframe
            timeframe: Timeframe in minutes
            
        Returns:
            List of detected FVGs
        """
        if len(df) < 3:
            return []
            
        fvgs = []
        
        # Convert to numpy arrays for faster processing
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        volumes = df['volume'].values
        times = df.index if hasattr(df.index, 'to_pydatetime') else df.index
        
        for i in range(len(df) - 2):
            # Extract three consecutive candles
            candle1_high, candle1_low = highs[i], lows[i]
            candle2_high, candle2_low = highs[i + 1], lows[i + 1]
            candle3_high, candle3_low = highs[i + 2], lows[i + 2]
            candle2_volume = volumes[i + 1]
            candle_time = times[i + 1]
            
            # Bullish FVG detection (upward move)
            if candle1_high < candle3_low:
                fvg_size = candle3_low - candle1_high
                
                if fvg_size >= self.config.min_fvg_size:
                    # Calculate strength based on price movement and volume
                    avg_range = np.mean([
                        candle1_high - candle1_low,
                        candle2_high - candle2_low,
                        candle3_high - candle3_low
                    ])
                    
                    strength = self._calculate_fvg_strength(
                        fvg_size, avg_range, candle2_volume, 
                        candle1_high, candle3_low
                    )
                    
                    # Apply filters
                    if self._passes_filters(strength, candle_time, timeframe):
                        fvg = FVG(
                            type=FVGType.BULLISH,
                            time=self._convert_time(candle_time),
                            top=candle1_high,
                            bottom=candle3_low,
                            size=fvg_size,
                            timeframe=timeframe,
                            volume=float(candle2_volume),
                            strength=float(strength)
                        )
                        fvgs.append(fvg)
                        
            # Bearish FVG detection (downward move)
            elif candle1_low > candle3_high:
                fvg_size = candle1_low - candle3_high
                
                if fvg_size >= self.config.min_fvg_size:
                    # Calculate strength
                    avg_range = np.mean([
                        candle1_high - candle1_low,
                        candle2_high - candle2_low,
                        candle3_high - candle3_low
                    ])
                    
                    strength = self._calculate_fvg_strength(
                        fvg_size, avg_range, candle2_volume,
                        candle3_high, candle1_low
                    )
                    
                    # Apply filters
                    if self._passes_filters(strength, candle_time, timeframe):
                        fvg = FVG(
                            type=FVGType.BEARISH,
                            time=self._convert_time(candle_time),
                            top=candle3_high,
                            bottom=candle1_low,
                            size=fvg_size,
                            timeframe=timeframe,
                            volume=float(candle2_volume),
                            strength=float(strength)
                        )
                        fvgs.append(fvg)
                        
        return fvgs
        
    def detect_fvgs_multi_timeframe(self, timeframe_data: TimeframeData) -> Dict[int, FVGList]:
        """
        Detect FVGs across all timeframes.
        
        Args:
            timeframe_data: Dictionary of OHLCV data by timeframe
            
        Returns:
            Dictionary of FVGs by timeframe
        """
        all_fvgs = {}
        
        for timeframe in self.timeframes:
            if timeframe in timeframe_data:
                df = timeframe_data[timeframe]
                if not df.empty:
                    fvgs = self.detect_fvgs_timeframe(df, timeframe)
                    all_fvgs[timeframe] = fvgs
                    
        self.detected_fvgs = all_fvgs
        return all_fvgs
        
    def find_confluence_areas(self, fvgs_by_timeframe: Optional[Dict[int, FVGList]] = None) -> List[ConfluenceArea]:
        """
        Find confluence areas where FVGs from multiple timeframes overlap.
        
        Args:
            fvgs_by_timeframe: FVGs by timeframe (uses detected FVGs if None)
            
        Returns:
            List of confluence areas
        """
        if fvgs_by_timeframe is None:
            fvgs_by_timeframe = self.detected_fvgs
            
        # Collect all FVGs
        all_fvgs = []
        for timeframe, fvgs in fvgs_by_timeframe.items():
            for fvg in fvgs:
                all_fvgs.append(fvg)
                
        if not all_fvgs:
            return []
            
        # Group FVGs by price level and time
        confluence_groups = self._group_fvgs_by_confluence(all_fvgs)
        
        # Create confluence areas
        confluence_areas = []
        for group in confluence_groups:
            if len(group) >= self.config.confluence_threshold:
                confluence_area = self._create_confluence_area(group)
                confluence_areas.append(confluence_area)
                
        self.confluence_areas = confluence_areas
        return confluence_areas
        
    def analyze_volume_at_confluence(self, price_data: pd.DataFrame, 
                                   confluence_areas: List[ConfluenceArea]) -> List[ConfluenceArea]:
        """
        Analyze volume patterns at confluence areas.
        
        Args:
            price_data: Price data with volume information
            confluence_areas: List of confluence areas to analyze
            
        Returns:
            Updated confluence areas with volume analysis
        """
        if price_data.empty or 'volume' not in price_data.columns:
            return confluence_areas
            
        volume_series = price_data['volume']
        
        for area in confluence_areas:
            # Find volume data around the confluence time
            volume_anomaly = self._detect_volume_anomaly_at_time(
                volume_series, area.time
            )
            area.volume_anomaly = volume_anomaly
            
        return confluence_areas
        
    def filter_by_volume_confirmation(self, confluence_areas: List[ConfluenceArea]) -> List[ConfluenceArea]:
        """
        Filter confluence areas based on volume confirmation.
        
        Args:
            confluence_areas: List of confluence areas to filter
            
        Returns:
            Filtered list with volume-confirmed areas
        """
        if not self.config.enable_volume_filter:
            return confluence_areas
            
        confirmed_areas = []
        for area in confluence_areas:
            if area.volume_anomaly and area.volume_anomaly.is_anomaly:
                confirmed_areas.append(area)
            elif area.volume_anomaly is None:
                # Include areas without volume data for flexibility
                confirmed_areas.append(area)
                
        return confirmed_areas
        
    def get_high_priority_setups(self, confluence_areas: List[ConfluenceArea], 
                               max_setups: int = 20) -> List[ConfluenceArea]:
        """
        Get high-priority setups based on confluence and volume analysis.
        
        Args:
            confluence_areas: List of confluence areas
            max_setups: Maximum number of setups to return
            
        Returns:
            High-priority setups sorted by score
        """
        # Calculate priority scores
        scored_areas = []
        for area in confluence_areas:
            priority_score = self._calculate_priority_score(area)
            area.confluence_score = priority_score  # Update the score
            scored_areas.append((priority_score, area))
            
        # Sort by priority score (descending)
        scored_areas.sort(key=lambda x: x[0], reverse=True)
        
        # Return top setups
        return [area for _, area in scored_areas[:max_setups]]
        
    def _calculate_fvg_strength(self, fvg_size: float, avg_range: float, 
                              volume: float, top: float, bottom: float) -> float:
        """
        Calculate the strength of an FVG.
        
        Args:
            fvg_size: Size of the FVG
            avg_range: Average candle range
            volume: Volume at the middle candle
            top: Top of the FVG
            bottom: Bottom of the FVG
            
        Returns:
            Strength score between 0 and 1
        """
        if avg_range == 0:
            return 0.0
            
        # Size component (40% weight)
        size_score = min(fvg_size / (avg_range * 2), 1.0)
        
        # Volume component (30% weight)
        volume_score = min(volume / 1000000, 1.0)  # Normalize volume
        
        # Price level component (20% weight) - higher price levels often have more significance
        price_level = (top + bottom) / 2
        price_score = min(price_level / 5000, 1.0)  # Normalize for MNQ levels
        
        # Range consistency component (10% weight)
        range_score = min(fvg_size / avg_range, 1.0)
        
        strength = (size_score * 0.4 + volume_score * 0.3 + 
                   price_score * 0.2 + range_score * 0.1)
                   
        return min(strength, 1.0)
        
    def _passes_filters(self, strength: float, time, timeframe: int) -> bool:
        """
        Check if FVG passes all configured filters.
        
        Args:
            strength: FVG strength score
            time: FVG timestamp
            timeframe: FVG timeframe
            
        Returns:
            True if FVG passes all filters
        """
        # Strength filter
        if self.config.enable_strength_filter and strength < self.config.min_strength_threshold:
            return False
            
        # Age filter
        if self.config.enable_age_filter:
            current_time = datetime.now()
            fvg_time = self._convert_time(time)
            age_minutes = (current_time - fvg_time).total_seconds() / 60
            if age_minutes > self.config.max_fvg_age_minutes:
                return False
                
        return True
        
    def _convert_time(self, time_input) -> datetime:
        """Convert various time inputs to datetime."""
        if isinstance(time_input, datetime):
            return time_input
        elif hasattr(time_input, 'to_pydatetime'):
            return time_input.to_pydatetime()
        elif isinstance(time_input, str):
            return pd.to_datetime(time_input).to_pydatetime()
        else:
            return pd.to_datetime(time_input).to_pydatetime()
            
    def _group_fvgs_by_confluence(self, all_fvgs: FVGList) -> List[List[FVG]]:
        """
        Group FVGs by confluence (price and time proximity).
        
        Args:
            all_fvgs: List of all FVGs
            
        Returns:
            List of FVG groups representing confluence areas
        """
        if not all_fvgs:
            return []
            
        # Sort by time
        sorted_fvgs = sorted(all_fvgs, key=lambda x: x.time)
        groups = []
        
        for fvg in sorted_fvgs:
            # Find existing group for this FVG
            assigned_group = None
            
            for group in groups:
                if self._fvg_belongs_to_group(fvg, group):
                    assigned_group = group
                    break
                    
            if assigned_group is None:
                # Create new group
                groups.append([fvg])
            else:
                # Add to existing group
                assigned_group.append(fvg)
                
        return groups
        
    def _fvg_belongs_to_group(self, fvg: FVG, group: List[FVG]) -> bool:
        """
        Check if an FVG belongs to a confluence group.
        
        Args:
            fvg: FVG to check
            group: Existing confluence group
            
        Returns:
            True if FVG belongs to the group
        """
        for group_fvg in group:
            # Check time proximity
            time_diff = abs((fvg.time - group_fvg.time).total_seconds())
            if time_diff > self.config.time_tolerance_minutes * 60:
                continue
                
            # Check price overlap
            if fvg.overlaps_with(group_fvg, self.config.price_tolerance):
                return True
                
        return False
        
    def _create_confluence_area(self, fvgs: List[FVG]) -> ConfluenceArea:
        """
        Create a confluence area from a group of FVGs.
        
        Args:
            fvgs: List of overlapping FVGs
            
        Returns:
            Confluence area object
        """
        # Calculate confluence metrics
        unique_timeframes = list(set(fvg.timeframe for fvg in fvgs))
        timeframe_count = len(unique_timeframes)
        
        # Calculate price level (average of all FVG midpoints)
        price_levels = [(fvg.top + fvg.bottom) / 2 for fvg in fvgs]
        price_level = np.mean(price_levels)
        
        # Calculate confluence score
        confluence_score = self._calculate_confluence_score(fvgs, timeframe_count)
        
        # Use the earliest time as the confluence time
        confluence_time = min(fvg.time for fvg in fvgs)
        
        return ConfluenceArea(
            time=confluence_time,
            price_level=price_level,
            fvgs=fvgs,
            timeframe_count=timeframe_count,
            timeframes=unique_timeframes,
            confluence_score=confluence_score
        )
        
    def _calculate_confluence_score(self, fvgs: List[FVG], timeframe_count: int) -> float:
        """
        Calculate confluence score for a group of FVGs.
        
        Args:
            fvgs: List of FVGs in the confluence area
            timeframe_count: Number of unique timeframes
            
        Returns:
            Confluence score between 0 and 100
        """
        # Timeframe contribution (70% weight)
        timeframe_score = (timeframe_count / len(self.timeframes)) * 70
        
        # Strength contribution (20% weight)
        avg_strength = np.mean([fvg.strength for fvg in fvgs])
        strength_score = avg_strength * 20
        
        # Volume contribution (10% weight)
        total_volume = sum(fvg.volume for fvg in fvgs)
        volume_score = min(total_volume / 5000000 * 10, 10)  # Normalize volume
        
        return timeframe_score + strength_score + volume_score
        
    def _detect_volume_anomaly_at_time(self, volume_series: pd.Series, 
                                     target_time: datetime) -> VolumeAnomaly:
        """
        Detect volume anomaly at a specific time.
        
        Args:
            volume_series: Volume data series
            target_time: Time to check for volume anomaly
            
        Returns:
            Volume anomaly information
        """
        if len(volume_series) < self.config.volume_period:
            return VolumeAnomaly(
                is_anomaly=False,
                multiplier=0.0,
                current_volume=0.0,
                average_volume=0.0,
                period=self.config.volume_period,
                threshold=self.config.volume_multiplier
            )
            
        # Calculate volume moving average
        volume_ma = volume_series.tail(self.config.volume_period).mean()
        
        # Find volume closest to target time
        current_volume = volume_series.iloc[-1]  # Use most recent volume
        
        # Check for anomaly
        multiplier = current_volume / volume_ma if volume_ma > 0 else 0
        is_anomaly = multiplier >= self.config.volume_multiplier
        
        return VolumeAnomaly(
            is_anomaly=is_anomaly,
            multiplier=multiplier,
            current_volume=float(current_volume),
            average_volume=float(volume_ma),
            period=self.config.volume_period,
            threshold=self.config.volume_multiplier
        )
        
    def _calculate_priority_score(self, confluence_area: ConfluenceArea) -> float:
        """
        Calculate priority score for a confluence area.
        
        Args:
            confluence_area: Confluence area to score
            
        Returns:
            Priority score between 0 and 100
        """
        base_score = confluence_area.confluence_score
        
        # Volume bonus
        volume_bonus = 0.0
        if confluence_area.volume_anomaly and confluence_area.volume_anomaly.is_anomaly:
            volume_bonus = min(confluence_area.volume_anomaly.multiplier * 5, 20)
            
        # Timeframe diversity bonus
        diversity_bonus = min(confluence_area.timeframe_count * 2, 10)
        
        # Strength bonus
        avg_strength = np.mean([fvg.strength for fvg in confluence_area.fvgs])
        strength_bonus = avg_strength * 10
        
        total_score = base_score + volume_bonus + diversity_bonus + strength_bonus
        return min(total_score, 100)
        
    def get_statistics(self) -> Dict:
        """
        Get detection statistics.
        
        Returns:
            Dictionary containing detection statistics
        """
        total_fvgs = sum(len(fvgs) for fvgs in self.detected_fvgs.values())
        fvgs_by_type = {FVGType.BULLISH: 0, FVGType.BEARISH: 0}
        fvgs_by_timeframe = {}
        
        for timeframe, fvgs in self.detected_fvgs.items():
            fvgs_by_timeframe[timeframe] = len(fvgs)
            for fvg in fvgs:
                fvgs_by_type[fvg.type] += 1
                
        return {
            'total_fvgs_detected': total_fvgs,
            'fvgs_by_type': {k.value: v for k, v in fvgs_by_type.items()},
            'fvgs_by_timeframe': fvgs_by_timeframe,
            'confluence_areas_found': len(self.confluence_areas),
            'timeframes_analyzed': len(self.detected_fvgs),
            'detection_config': {
                'min_fvg_size': self.config.min_fvg_size,
                'min_strength_threshold': self.config.min_strength_threshold,
                'confluence_threshold': self.config.confluence_threshold,
                'volume_multiplier': self.config.volume_multiplier
            }
        }
        
    def clear_cache(self) -> None:
        """Clear cached detection results."""
        self.detected_fvgs.clear()
        self.confluence_areas.clear()


# Utility functions for FVG detection
def detect_fvgs_simple(df: pd.DataFrame, timeframe: int, 
                      min_size: float = 0.25) -> FVGList:
    """
    Simple FVG detection function for basic use cases.
    
    Args:
        df: OHLCV data
        timeframe: Timeframe in minutes
        min_size: Minimum FVG size
        
    Returns:
        List of detected FVGs
    """
    config = FVGDetectorConfig(
        min_fvg_size=min_size,
        enable_volume_filter=False,
        enable_strength_filter=False,
        enable_age_filter=False
    )
    detector = FVGDetector(config)
    return detector.detect_fvgs_timeframe(df, timeframe)


def merge_consecutive_fvgs(fvgs: FVGList, max_gap_minutes: int = 10) -> FVGList:
    """
    Merge consecutive FVGs of the same type.
    
    Args:
        fvgs: List of FVGs to merge
        max_gap_minutes: Maximum time gap for merging
        
    Returns:
        List of merged FVGs
    """
    if not fvgs:
        return []
        
    # Sort by time
    sorted_fvgs = sorted(fvgs, key=lambda x: x.time)
    merged = []
    
    current_group = [sorted_fvgs[0]]
    
    for fvg in sorted_fvgs[1:]:
        last_fvg = current_group[-1]
        
        # Check if FVGs should be merged
        time_gap = (fvg.time - last_fvg.time).total_seconds() / 60
        same_type = fvg.type == last_fvg.type
        price_overlap = fvg.overlaps_with(last_fvg, tolerance=0.5)
        
        if same_type and time_gap <= max_gap_minutes and price_overlap:
            current_group.append(fvg)
        else:
            # Merge current group and start new one
            if len(current_group) > 1:
                merged.append(_merge_fvg_group(current_group))
            else:
                merged.append(current_group[0])
            current_group = [fvg]
            
    # Handle last group
    if len(current_group) > 1:
        merged.append(_merge_fvg_group(current_group))
    else:
        merged.append(current_group[0])
        
    return merged


def _merge_fvg_group(fvg_group: List[FVG]) -> FVG:
    """
    Merge a group of FVGs into a single FVG.
    
    Args:
        fvg_group: Group of FVGs to merge
        
    Returns:
        Merged FVG
    """
    if not fvg_group:
        raise ValueError("Cannot merge empty FVG group")
        
    # Use the earliest time
    merged_time = min(fvg.time for fvg in fvg_group)
    
    # Use the smallest timeframe
    merged_timeframe = min(fvg.timeframe for fvg in fvg_group)
    
    # Merge price ranges
    merged_top = max(fvg.top for fvg in fvg_group)
    merged_bottom = min(fvg.bottom for fvg in fvg_group)
    merged_size = merged_top - merged_bottom
    
    # Sum volumes and average strength
    merged_volume = sum(fvg.volume for fvg in fvg_group)
    merged_strength = np.mean([fvg.strength for fvg in fvg_group])
    
    # All FVGs in group should have same type
    merged_type = fvg_group[0].type
    
    return FVG(
        type=merged_type,
        time=merged_time,
        top=merged_top,
        bottom=merged_bottom,
        size=merged_size,
        timeframe=merged_timeframe,
        volume=merged_volume,
        strength=merged_strength
    )