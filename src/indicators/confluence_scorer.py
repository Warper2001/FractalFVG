"""
Confluence Scorer for FVG Confluence Trading Strategy.

This module provides comprehensive confluence scoring capabilities that combine
multi-timeframe FVG alignment with volume confirmation and ML-based enhancements
to identify high-probability trading opportunities.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from .base_indicator import FVGIndicator
from ..models.fvg import FVG, FVGType
from ..models.confluence_score import ConfluenceScore, TimeframeConfluence, ConfluenceHistory
from ..data.volume_analyzer import VolumeAnalyzer
from ..utils.config import StrategyConfig

logger = logging.getLogger(__name__)


class ConfluenceScorer(FVGIndicator):
    """
    Advanced confluence scoring indicator for multi-timeframe FVG analysis.
    
    Combines:
    - Multi-timeframe FVG alignment (70% weight)
    - Volume confirmation (30% weight)
    - ML-based timeframe importance scoring
    - Real-time confluence monitoring
    """
    
    def __init__(self, name: str = "Confluence_Scorer", timeframes: List[int] = None,
                 volume_analyzer: Optional[VolumeAnalyzer] = None,
                 config: Optional[StrategyConfig] = None):
        """
        Initialize Confluence Scorer.
        
        Args:
            name: Indicator name
            timeframes: List of timeframes to analyze
            volume_analyzer: Volume analyzer instance
            config: Strategy configuration
        """
        super().__init__(name, timeframe=1)  # Base timeframe doesn't apply to confluence
        
        self.timeframes = timeframes or list(range(1, 61))  # 1-60 minutes
        self.volume_analyzer = volume_analyzer or VolumeAnalyzer()
        self.config = config or StrategyConfig()
        
        # Confluence scoring parameters
        self.confluence_weights = self.config.confluence_weights
        self.min_confluence_score = self.config.min_confluence_score
        
        # Data storage
        self.fvg_by_timeframe: Dict[int, List[FVG]] = defaultdict(list)
        self.volume_analyses: Dict[int, Dict[str, Any]] = {}
        self.ml_scores: Dict[int, float] = {}
        self.confluence_scores: List[ConfluenceScore] = []
        self.confluence_history = ConfluenceHistory()
        
        # ML model for timeframe importance (placeholder)
        self.ml_timeframe_weights: Dict[int, float] = {}
        self._initialize_ml_weights()
        
        # Performance tracking
        self.scoring_stats = {
            'total_confluences': 0,
            'high_quality_confluences': 0,
            'volume_confirmations': 0,
            'ml_enhancements': 0,
            'last_scoring_time': None
        }
        
        logger.info(f"Confluence Scorer initialized: {name}")
        logger.debug(f"Timeframes: {self.timeframes}, Confluence weights: {self.confluence_weights}")
        
    def _initialize_ml_weights(self) -> None:
        """Initialize ML-based timeframe importance weights."""
        # Base weights derived from historical analysis
        for timeframe in self.timeframes:
            if timeframe >= 30:
                self.ml_timeframe_weights[timeframe] = 0.9  # Very high importance
            elif timeframe >= 15:
                self.ml_timeframe_weights[timeframe] = 0.7  # High importance
            elif timeframe >= 5:
                self.ml_timeframe_weights[timeframe] = 0.5  # Medium importance
            else:
                self.ml_timeframe_weights[timeframe] = 0.3  # Lower importance
                
        logger.debug(f"Initialized ML weights for {len(self.ml_timeframe_weights)} timeframes")
        
    def add_fvg_data(self, timeframe: int, fvgs: List[FVG]) -> None:
        """
        Add FVG data for a specific timeframe.
        
        Args:
            timeframe: Timeframe in minutes
            fvgs: List of FVGs from this timeframe
        """
        if timeframe not in self.timeframes:
            logger.warning(f"Timeframe {timeframe} not in configured timeframes")
            return
            
        # Store FVGs
        self.fvg_by_timeframe[timeframe] = fvgs
        
        # Analyze volume for this timeframe
        if fvgs:
            latest_fvg = fvgs[-1]  # Most recent FVG
            volume_analysis = self.volume_analyzer.analyze_volume(
                latest_fvg.volume, 
                latest_fvg.time, 
                timeframe
            )
            self.volume_analyses[timeframe] = volume_analysis
            
        # Calculate ML score for this timeframe
        self.ml_scores[timeframe] = self._calculate_ml_score(timeframe, fvgs)
        
        logger.debug(f"Added {len(fvgs)} FVGs for {timeframe}min timeframe")
        
    def _calculate_ml_score(self, timeframe: int, fvgs: List[FVG]) -> float:
        """
        Calculate ML-based score for timeframe importance.
        
        Args:
            timeframe: Timeframe in minutes
            fvgs: List of FVGs from this timeframe
            
        Returns:
            ML score between 0 and 1
        """
        if not fvgs:
            return 0.0
            
        # Base ML weight from historical performance
        base_weight = self.ml_timeframe_weights.get(timeframe, 0.5)
        
        # Adjust based on recent FVG quality
        recent_fvgs = fvgs[-5:]  # Last 5 FVGs
        if recent_fvgs:
            avg_strength = np.mean([fvg.strength for fvg in recent_fvgs])
            avg_size = np.mean([fvg.size for fvg in recent_fvgs])
            
            # Quality adjustment
            quality_factor = (avg_strength * 0.6 + min(avg_size / 2.0, 1.0) * 0.4)
            
            # Volume confirmation adjustment
            volume_analysis = self.volume_analyses.get(timeframe, {})
            volume_factor = 1.2 if volume_analysis.get('is_anomaly', False) else 1.0
            
            ml_score = base_weight * quality_factor * volume_factor
        else:
            ml_score = base_weight
            
        return min(ml_score, 1.0)
        
    def calculate_confluence_scores(self, price_tolerance: float = 0.5) -> List[ConfluenceScore]:
        """
        Calculate confluence scores for all price levels.
        
        Args:
            price_tolerance: Price tolerance for grouping FVGs
            
        Returns:
            List of confluence scores
        """
        try:
            # Collect all FVGs from all timeframes
            all_fvgs = []
            for timeframe, fvgs in self.fvg_by_timeframe.items():
                for fvg in fvgs:
                    all_fvgs.append((timeframe, fvg))
                    
            if not all_fvgs:
                return []
                
            # Group FVGs by price level
            price_groups = self._group_fvgs_by_price(all_fvgs, price_tolerance)
            
            # Calculate confluence score for each price group
            confluence_scores = []
            for price_level, fvgs_group in price_groups.items():
                confluence_score = self._calculate_single_confluence_score(price_level, fvgs_group)
                if confluence_score:
                    confluence_scores.append(confluence_score)
                    
            # Sort by final score (descending)
            confluence_scores.sort(key=lambda cs: cs.final_score, reverse=True)
            
            # Store and track
            self.confluence_scores = confluence_scores
            self._update_scoring_stats(confluence_scores)
            
            logger.info(f"Calculated {len(confluence_scores)} confluence scores")
            if confluence_scores:
                high_quality = [cs for cs in confluence_scores if cs.is_high_quality()]
                logger.info(f"High quality confluences: {len(high_quality)}/{len(confluence_scores)}")
                
            return confluence_scores
            
        except Exception as e:
            logger.error(f"Error calculating confluence scores: {e}")
            return []
            
    def _group_fvgs_by_price(self, all_fvgs: List[Tuple[int, FVG]], 
                            tolerance: float) -> Dict[float, List[Tuple[int, FVG]]]:
        """
        Group FVGs by price level within tolerance.
        
        Args:
            all_fvgs: List of (timeframe, FVG) tuples
            tolerance: Price tolerance for grouping
            
        Returns:
            Dictionary of price level to FVG groups
        """
        price_groups = {}
        
        for timeframe, fvg in all_fvgs:
            # Find existing price group within tolerance
            assigned = False
            for price_level in price_groups:
                if abs(price_level - fvg.mid_price) <= tolerance:
                    price_groups[price_level].append((timeframe, fvg))
                    assigned = True
                    break
                    
            # Create new price group if not assigned
            if not assigned:
                price_groups[fvg.mid_price] = [(timeframe, fvg)]
                
        return price_groups
        
    def _calculate_single_confluence_score(self, price_level: float, 
                                         fvgs_group: List[Tuple[int, FVG]]) -> Optional[ConfluenceScore]:
        """
        Calculate confluence score for a single price level.
        
        Args:
            price_level: Price level for confluence
            fvgs_group: List of (timeframe, FVG) tuples at this price level
            
        Returns:
            ConfluenceScore or None if insufficient data
        """
        if len(fvgs_group) < 2:  # Need at least 2 timeframes for confluence
            return None
            
        # Extract FVGs and prepare data
        fvgs = [fvg for _, fvg in fvgs_group]
        volume_analyses = {}
        ml_scores = {}
        
        for timeframe, fvg in fvgs_group:
            volume_analyses[timeframe] = self.volume_analyses.get(timeframe, {})
            ml_scores[timeframe] = self.ml_scores.get(timeframe, 0.0)
            
        try:
            # Create confluence score
            confluence_score = ConfluenceScore.from_fvg_list(
                fvgs=fvgs,
                volume_analyses=volume_analyses,
                ml_scores=ml_scores,
                calculation_time=datetime.now()
            )
            
            return confluence_score
            
        except Exception as e:
            logger.error(f"Error calculating confluence score for price {price_level}: {e}")
            return None
            
    def _update_scoring_stats(self, confluence_scores: List[ConfluenceScore]) -> None:
        """Update scoring statistics."""
        self.scoring_stats['total_confluences'] += len(confluence_scores)
        self.scoring_stats['high_quality_confluences'] += len([cs for cs in confluence_scores if cs.is_high_quality()])
        self.scoring_stats['volume_confirmations'] += len([cs for cs in confluence_scores if cs.volume_score > 0.2])
        self.scoring_stats['ml_enhancements'] += len([cs for cs in confluence_scores if cs.ml_enhanced_score > 0.05])
        self.scoring_stats['last_scoring_time'] = datetime.now()
        
    def get_high_quality_confluences(self, min_score: float = 0.6) -> List[ConfluenceScore]:
        """
        Get high-quality confluence scores.
        
        Args:
            min_score: Minimum confluence score
            
        Returns:
            List of high-quality confluence scores
        """
        return [cs for cs in self.confluence_scores if cs.final_score >= min_score and cs.is_high_quality()]
        
    def get_confluence_by_timeframe_count(self, min_timeframes: int = 3) -> List[ConfluenceScore]:
        """
        Get confluence scores with minimum timeframe count.
        
        Args:
            min_timeframes: Minimum number of timeframes
            
        Returns:
            List of confluence scores meeting criteria
        """
        return [cs for cs in self.confluence_scores if cs.total_timeframes >= min_timeframes]
        
    def get_volume_confirmed_confluences(self) -> List[ConfluenceScore]:
        """
        Get confluence scores with volume confirmation.
        
        Returns:
            List of volume-confirmed confluence scores
        """
        return [cs for cs in self.confluence_scores if cs.volume_score > 0.2]
        
    def analyze_confluence_performance(self, lookback_periods: int = 100) -> Dict[str, Any]:
        """
        Analyze confluence performance over recent periods.
        
        Args:
            lookback_periods: Number of periods to analyze
            
        Returns:
            Performance analysis results
        """
        recent_confluences = self.confluence_scores[-lookback_periods:]
        
        if not recent_confluences:
            return {'error': 'No confluence data available'}
            
        # Calculate statistics
        scores = [cs.final_score for cs in recent_confluences]
        timeframe_counts = [cs.total_timeframes for cs in recent_confluences]
        volume_scores = [cs.volume_score for cs in recent_confluences]
        
        analysis = {
            'periods_analyzed': len(recent_confluences),
            'score_statistics': {
                'mean': np.mean(scores),
                'median': np.median(scores),
                'std': np.std(scores),
                'min': min(scores),
                'max': max(scores)
            },
            'timeframe_statistics': {
                'mean_timeframes': np.mean(timeframe_counts),
                'median_timeframes': np.median(timeframe_counts),
                'min_timeframes': min(timeframe_counts),
                'max_timeframes': max(timeframe_counts)
            },
            'volume_statistics': {
                'mean_volume_score': np.mean(volume_scores),
                'volume_confirmation_rate': len([cs for cs in recent_confluences if cs.volume_score > 0.2]) / len(recent_confluences)
            },
            'quality_distribution': {
                'high_quality': len([cs for cs in recent_confluences if cs.is_high_quality()]),
                'medium_quality': len([cs for cs in recent_confluences if 0.4 <= cs.final_score < 0.6]),
                'low_quality': len([cs for cs in recent_confluences if cs.final_score < 0.4])
            }
        }
        
        return analysis
        
    def update_ml_weights(self, performance_data: Dict[str, Any]) -> None:
        """
        Update ML-based timeframe weights based on performance.
        
        Args:
            performance_data: Performance data for weight updates
        """
        try:
            # Simple weight update based on recent performance
            for timeframe in self.timeframes:
                current_weight = self.ml_timeframe_weights.get(timeframe, 0.5)
                
                # Get performance for this timeframe
                timeframe_performance = performance_data.get(f'timeframe_{timeframe}', {})
                success_rate = timeframe_performance.get('success_rate', 0.5)
                
                # Update weight with learning rate
                learning_rate = 0.1
                weight_adjustment = (success_rate - 0.5) * learning_rate
                new_weight = max(0.1, min(1.0, current_weight + weight_adjustment))
                
                self.ml_timeframe_weights[timeframe] = new_weight
                
            logger.debug("Updated ML weights based on performance data")
            
        except Exception as e:
            logger.error(f"Error updating ML weights: {e}")
            
    def get_ml_importance_ranking(self) -> List[Tuple[int, float]]:
        """
        Get ML-based timeframe importance ranking.
        
        Returns:
            List of (timeframe, weight) tuples sorted by weight
        """
        return sorted(self.ml_timeframe_weights.items(), key=lambda x: x[1], reverse=True)
        
    def get_scoring_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive scoring statistics.
        
        Returns:
            Scoring statistics
        """
        stats = self.scoring_stats.copy()
        
        # Add current state
        stats.update({
            'active_timeframes': len(self.fvg_by_timeframe),
            'total_fvgs': sum(len(fvgs) for fvgs in self.fvg_by_timeframe.values()),
            'current_confluence_scores': len(self.confluence_scores),
            'ml_weights_count': len(self.ml_timeframe_weights),
            'volume_analyzer_stats': self.volume_analyzer.get_analysis_statistics()
        })
        
        # Calculate rates
        if stats['total_confluences'] > 0:
            stats['high_quality_rate'] = stats['high_quality_confluences'] / stats['total_confluences']
            stats['volume_confirmation_rate'] = stats['volume_confirmations'] / stats['total_confluences']
            stats['ml_enhancement_rate'] = stats['ml_enhancements'] / stats['total_confluences']
        else:
            stats['high_quality_rate'] = 0.0
            stats['volume_confirmation_rate'] = 0.0
            stats['ml_enhancement_rate'] = 0.0
            
        return stats
        
    def export_confluence_data(self, filename: str, include_history: bool = True) -> bool:
        """
        Export confluence data to file.
        
        Args:
            filename: Output filename
            include_history: Whether to include confluence history
            
        Returns:
            True if export successful
        """
        try:
            export_data = {
                'confluence_scores': [cs.to_dict() for cs in self.confluence_scores],
                'scoring_statistics': self.get_scoring_statistics(),
                'ml_weights': self.ml_timeframe_weights,
                'export_time': datetime.now().isoformat()
            }
            
            if include_history:
                export_data['confluence_history'] = {
                    'performance_metrics': self.confluence_history.get_performance_metrics(),
                    'total_records': len(self.confluence_history.confluence_scores)
                }
                
            if filename.endswith('.json'):
                import json
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            else:
                return False
                
            logger.info(f"Confluence data exported to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting confluence data: {e}")
            return False
            
    def reset_statistics(self) -> None:
        """Reset scoring statistics."""
        self.scoring_stats = {
            'total_confluences': 0,
            'high_quality_confluences': 0,
            'volume_confirmations': 0,
            'ml_enhancements': 0,
            'last_scoring_time': None
        }
        
        self.confluence_history = ConfluenceHistory()
        logger.debug("Confluence scoring statistics reset")
        
    def cleanup(self) -> None:
        """Clean up resources and data."""
        self.fvg_by_timeframe.clear()
        self.volume_analyses.clear()
        self.ml_scores.clear()
        self.confluence_scores.clear()
        self.ml_timeframe_weights.clear()
        
        if self.volume_analyzer:
            self.volume_analyzer.cleanup()
            
        self.reset_statistics()
        logger.debug("Confluence Scorer cleaned up")