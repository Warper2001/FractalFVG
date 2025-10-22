"""
Volume Analyzer for FVG Confluence Trading Strategy.

This module provides comprehensive volume analysis capabilities including
anomaly detection, session-based adjustments, and volume profile analysis
to enhance FVG detection with volume confirmation.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

from ..utils.config import StrategyConfig
from ..utils.helpers import validate_timeframe

logger = logging.getLogger(__name__)


class VolumeAnalyzer:
    """
    Advanced volume analysis for FVG confluence confirmation.
    
    Provides:
    - Volume anomaly detection (2x average, 20-period baseline)
    - Session-based volume adjustments (US session 2.0x, overnight 0.3x)
    - Volume profile analysis
    - Real-time volume monitoring
    """
    
    def __init__(self, symbol: str = "MNQ", config: Optional[StrategyConfig] = None):
        """
        Initialize Volume Analyzer.
        
        Args:
            symbol: Trading symbol
            config: Strategy configuration
        """
        self.symbol = symbol
        self.config = config or StrategyConfig()
        self.logger = logging.getLogger(__name__)
        
        # Volume analysis parameters
        self.baseline_period = self.config.volume_analysis["baseline_period"]  # 20 periods
        self.anomaly_threshold = self.config.volume_threshold  # 2.0x average
        self.session_multipliers = self.config.volume_analysis["session_multipliers"]
        
        # Data storage
        self.volume_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=self.baseline_period * 2))
        self.session_volumes: Dict[str, List[float]] = defaultdict(list)
        self.volume_profiles: Dict[int, Dict[str, Any]] = {}
        
        # Session detection
        self.us_session_start = 9 * 60 + 30  # 9:30 AM EST (570 minutes)
        self.us_session_end = 16 * 60  # 4:00 PM EST (960 minutes)
        
        # Performance tracking
        self.analysis_stats = {
            'total_analyses': 0,
            'anomalies_detected': 0,
            'session_adjustments': 0,
            'volume_profiles_generated': 0,
            'last_analysis_time': None
        }
        
        self.logger.info(f"Volume Analyzer initialized for {symbol}")
        self.logger.debug(f"Baseline period: {self.baseline_period}, Anomaly threshold: {self.anomaly_threshold}x")
        
    def analyze_volume(self, volume: float, timestamp: datetime, timeframe: int = 1) -> Dict[str, Any]:
        """
        Analyze volume for anomaly detection and session adjustments.
        
        Args:
            volume: Current volume
            timestamp: Timestamp of the volume data
            timeframe: Timeframe in minutes
            
        Returns:
            Volume analysis results
        """
        try:
            # Validate inputs
            if not validate_timeframe(timeframe):
                raise ValueError(f"Invalid timeframe: {timeframe}")
                
            if volume < 0:
                raise ValueError(f"Volume cannot be negative: {volume}")
                
            # Add to history
            self.volume_history[timeframe].append({
                'volume': volume,
                'timestamp': timestamp,
                'session': self._detect_session(timestamp)
            })
            
            # Perform analysis
            analysis_result = {
                'timestamp': timestamp,
                'timeframe': timeframe,
                'current_volume': volume,
                'session': self._detect_session(timestamp),
                'is_anomaly': False,
                'anomaly_multiplier': 0.0,
                'baseline_volume': 0.0,
                'adjusted_volume': volume,
                'session_multiplier': 1.0,
                'volume_percentile': 0.0,
                'volume_trend': 'neutral'
            }
            
            # Calculate baseline and detect anomalies
            if len(self.volume_history[timeframe]) >= self.baseline_period:
                analysis_result.update(self._detect_volume_anomaly(timeframe, volume))
                
            # Apply session-based adjustments
            analysis_result.update(self._apply_session_adjustments(analysis_result))
            
            # Calculate volume percentile
            analysis_result['volume_percentile'] = self._calculate_volume_percentile(timeframe, volume)
            
            # Determine volume trend
            analysis_result['volume_trend'] = self._determine_volume_trend(timeframe)
            
            # Update statistics
            self._update_analysis_stats(analysis_result)
            
            # Log significant events
            if analysis_result['is_anomaly']:
                self.logger.info(f"Volume anomaly detected [{timeframe}min]: {volume:.0f} "
                               f"({analysis_result['anomaly_multiplier']:.2f}x baseline) "
                               f"at {timestamp}")
                               
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing volume: {e}")
            return {
                'timestamp': timestamp,
                'timeframe': timeframe,
                'current_volume': volume,
                'error': str(e)
            }
            
    def _detect_volume_anomaly(self, timeframe: int, current_volume: float) -> Dict[str, Any]:
        """
        Detect volume anomalies using 20-period baseline.
        
        Args:
            timeframe: Timeframe in minutes
            current_volume: Current volume to analyze
            
        Returns:
            Anomaly detection results
        """
        history = list(self.volume_history[timeframe])
        if len(history) < self.baseline_period:
            return {
                'baseline_volume': 0.0,
                'is_anomaly': False,
                'anomaly_multiplier': 0.0
            }
            
        # Calculate baseline (average of last baseline_period volumes)
        recent_volumes = [entry['volume'] for entry in history[-self.baseline_period:]]
        baseline_volume = np.mean(recent_volumes)
        
        # Detect anomaly (2x+ average)
        if baseline_volume > 0:
            anomaly_multiplier = current_volume / baseline_volume
            is_anomaly = anomaly_multiplier >= self.anomaly_threshold
        else:
            anomaly_multiplier = 0.0
            is_anomaly = False
            
        return {
            'baseline_volume': baseline_volume,
            'is_anomaly': is_anomaly,
            'anomaly_multiplier': anomaly_multiplier
        }
        
    def _apply_session_adjustments(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply session-based volume adjustments.
        
        Args:
            analysis_result: Current analysis result
            
        Returns:
            Adjusted analysis result
        """
        session = analysis_result['session']
        session_multiplier = self.session_multipliers.get(session, 1.0)
        
        # Apply session adjustment
        adjusted_volume = analysis_result['current_volume'] * session_multiplier
        
        # Re-calculate anomaly with adjusted volume
        if analysis_result.get('baseline_volume', 0) > 0:
            adjusted_multiplier = adjusted_volume / analysis_result['baseline_volume']
            adjusted_is_anomaly = adjusted_multiplier >= self.anomaly_threshold
        else:
            adjusted_multiplier = 0.0
            adjusted_is_anomaly = False
            
        return {
            'session_multiplier': session_multiplier,
            'adjusted_volume': adjusted_volume,
            'adjusted_anomaly_multiplier': adjusted_multiplier,
            'adjusted_is_anomaly': adjusted_is_anomaly
        }
        
    def _detect_session(self, timestamp: datetime) -> str:
        """
        Detect trading session based on timestamp.
        
        Args:
            timestamp: Timestamp to analyze
            
        Returns:
            Session identifier
        """
        # Convert to minutes since midnight
        minutes_since_midnight = timestamp.hour * 60 + timestamp.minute
        
        # Check for US session (9:30 AM - 4:00 PM EST, Monday-Friday)
        if (timestamp.weekday() < 5 and  # Monday-Friday
            self.us_session_start <= minutes_since_midnight <= self.us_session_end):
            return "us_session"
        elif minutes_since_midnight < self.us_session_start:
            return "overnight"
        else:
            return "after_hours"
            
    def _calculate_volume_percentile(self, timeframe: int, current_volume: float) -> float:
        """
        Calculate volume percentile relative to historical data.
        
        Args:
            timeframe: Timeframe in minutes
            current_volume: Current volume
            
        Returns:
            Volume percentile (0-100)
        """
        history = list(self.volume_history[timeframe])
        if len(history) < 10:
            return 50.0  # Default to middle percentile
            
        volumes = [entry['volume'] for entry in history]
        percentile = (np.sum(np.array(volumes) <= current_volume) / len(volumes)) * 100
        
        return min(percentile, 100.0)
        
    def _determine_volume_trend(self, timeframe: int) -> str:
        """
        Determine volume trend based on recent data.
        
        Args:
            timeframe: Timeframe in minutes
            
        Returns:
            Volume trend ('increasing', 'decreasing', 'neutral')
        """
        history = list(self.volume_history[timeframe])
        if len(history) < 10:
            return "neutral"
            
        # Get last 10 volumes
        recent_volumes = [entry['volume'] for entry in history[-10:]]
        
        # Calculate trend
        first_half = np.mean(recent_volumes[:5])
        second_half = np.mean(recent_volumes[5:])
        
        if second_half > first_half * 1.1:
            return "increasing"
        elif second_half < first_half * 0.9:
            return "decreasing"
        else:
            return "neutral"
            
    def _update_analysis_stats(self, analysis_result: Dict[str, Any]) -> None:
        """Update analysis statistics."""
        self.analysis_stats['total_analyses'] += 1
        
        if analysis_result.get('is_anomaly', False):
            self.analysis_stats['anomalies_detected'] += 1
            
        if analysis_result.get('session_multiplier', 1.0) != 1.0:
            self.analysis_stats['session_adjustments'] += 1
            
        self.analysis_stats['last_analysis_time'] = analysis_result['timestamp']
        
    def generate_volume_profile(self, timeframe: int, lookback_periods: int = 100) -> Dict[str, Any]:
        """
        Generate volume profile for analysis.
        
        Args:
            timeframe: Timeframe in minutes
            lookback_periods: Number of periods to analyze
            
        Returns:
            Volume profile statistics
        """
        try:
            history = list(self.volume_history[timeframe])
            if len(history) < 10:
                return {'error': 'Insufficient data for volume profile'}
                
            # Get recent data
            recent_data = history[-lookback_periods:]
            volumes = [entry['volume'] for entry in recent_data]
            
            # Calculate profile statistics
            profile = {
                'timeframe': timeframe,
                'periods_analyzed': len(recent_data),
                'total_volume': sum(volumes),
                'average_volume': np.mean(volumes),
                'median_volume': np.median(volumes),
                'std_volume': np.std(volumes),
                'min_volume': min(volumes),
                'max_volume': max(volumes),
                'volume_range': max(volumes) - min(volumes),
                'volume_distribution': self._calculate_volume_distribution(volumes),
                'session_breakdown': self._analyze_session_volumes(recent_data),
                'trend_analysis': self._analyze_volume_trends(recent_data)
            }
            
            # Store profile
            self.volume_profiles[timeframe] = profile
            self.analysis_stats['volume_profiles_generated'] += 1
            
            self.logger.debug(f"Volume profile generated for {timeframe}min: "
                            f"Avg={profile['average_volume']:.0f}, "
                            f"Range={profile['volume_range']:.0f}")
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Error generating volume profile: {e}")
            return {'error': str(e)}
            
    def _calculate_volume_distribution(self, volumes: List[float]) -> Dict[str, Any]:
        """Calculate volume distribution statistics."""
        volumes_array = np.array(volumes)
        
        return {
            'percentiles': {
                'p25': np.percentile(volumes_array, 25),
                'p50': np.percentile(volumes_array, 50),
                'p75': np.percentile(volumes_array, 75),
                'p90': np.percentile(volumes_array, 90),
                'p95': np.percentile(volumes_array, 95)
            },
            'deciles': {
                f'd{i}': np.percentile(volumes_array, i * 10) for i in range(1, 10)
            }
        }
        
    def _analyze_session_volumes(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze volume by trading session."""
        session_volumes = defaultdict(list)
        
        for entry in data:
            session = entry['session']
            session_volumes[session].append(entry['volume'])
            
        session_stats = {}
        for session, volumes in session_volumes.items():
            if volumes:
                session_stats[session] = {
                    'count': len(volumes),
                    'total': sum(volumes),
                    'average': np.mean(volumes),
                    'std': np.std(volumes),
                    'min': min(volumes),
                    'max': max(volumes)
                }
                
        return session_stats
        
    def _analyze_volume_trends(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze volume trends over time."""
        if len(data) < 20:
            return {'error': 'Insufficient data for trend analysis'}
            
        volumes = [entry['volume'] for entry in data]
        
        # Calculate moving averages
        short_ma = pd.Series(volumes).rolling(window=5).mean().iloc[-1]
        long_ma = pd.Series(volumes).rolling(window=20).mean().iloc[-1]
        
        # Determine trend
        if short_ma > long_ma * 1.05:
            trend = 'bullish'
        elif short_ma < long_ma * 0.95:
            trend = 'bearish'
        else:
            trend = 'neutral'
            
        return {
            'short_ma': short_ma,
            'long_ma': long_ma,
            'trend': trend,
            'ma_ratio': short_ma / long_ma if long_ma > 0 else 0
        }
        
    def get_volume_anomaly_score(self, timeframe: int, lookback_periods: int = 20) -> float:
        """
        Calculate overall volume anomaly score for a timeframe.
        
        Args:
            timeframe: Timeframe in minutes
            lookback_periods: Number of periods to analyze
            
        Returns:
            Anomaly score between 0 and 1
        """
        history = list(self.volume_history[timeframe])
        if len(history) < lookback_periods:
            return 0.0
            
        recent_data = history[-lookback_periods:]
        anomaly_count = sum(1 for entry in recent_data if entry.get('is_anomaly', False))
        
        return anomaly_count / lookback_periods
        
    def get_session_volume_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive session volume statistics.
        
        Returns:
            Session volume statistics
        """
        session_stats = {}
        
        for session in ['us_session', 'overnight', 'after_hours']:
            session_data = []
            for timeframe_data in self.volume_history.values():
                session_data.extend([entry for entry in timeframe_data if entry['session'] == session])
                
            if session_data:
                volumes = [entry['volume'] for entry in session_data]
                session_stats[session] = {
                    'count': len(volumes),
                    'total_volume': sum(volumes),
                    'average_volume': np.mean(volumes),
                    'std_volume': np.std(volumes),
                    'min_volume': min(volumes),
                    'max_volume': max(volumes),
                    'anomaly_rate': sum(1 for entry in session_data if entry.get('is_anomaly', False)) / len(session_data)
                }
            else:
                session_stats[session] = {'count': 0}
                
        return session_stats
        
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive volume analysis statistics.
        
        Returns:
            Analysis statistics
        """
        stats = self.analysis_stats.copy()
        
        # Add current state
        stats.update({
            'active_timeframes': len(self.volume_history),
            'total_data_points': sum(len(data) for data in self.volume_history.values()),
            'volume_profiles_count': len(self.volume_profiles),
            'session_stats': self.get_session_volume_stats()
        })
        
        # Calculate anomaly rates
        if stats['total_analyses'] > 0:
            stats['anomaly_rate'] = stats['anomalies_detected'] / stats['total_analyses']
            stats['session_adjustment_rate'] = stats['session_adjustments'] / stats['total_analyses']
        else:
            stats['anomaly_rate'] = 0.0
            stats['session_adjustment_rate'] = 0.0
            
        return stats
        
    def reset_statistics(self) -> None:
        """Reset analysis statistics."""
        self.analysis_stats = {
            'total_analyses': 0,
            'anomalies_detected': 0,
            'session_adjustments': 0,
            'volume_profiles_generated': 0,
            'last_analysis_time': None
        }
        
        self.logger.debug("Volume analysis statistics reset")
        
    def cleanup(self) -> None:
        """Clean up resources and data."""
        self.volume_history.clear()
        self.session_volumes.clear()
        self.volume_profiles.clear()
        self.reset_statistics()
        
        self.logger.debug("Volume Analyzer cleaned up")